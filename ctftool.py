#!/usr/bin/env python3

import argparse
import glob
import json
import os
import sys
import re
import traceback
import subprocess
from typing import Any, Dict, Iterable, List, Optional

import colorama
import requests
import yaml
from colorama import Fore, Style

UPSTREAM = "https://raw.githubusercontent.com/jedevc/mini-ctf-tool/master/ctftool.py"


def main():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers()

    list_parser = subparsers.add_parser("list", help="list all challenges")
    list_parser.add_argument(
        "--verbose", "-v", action="store_true", help="increase verbosity"
    )
    list_parser.set_defaults(func=list_challenges)

    validate_parser = subparsers.add_parser(
        "validate", help="validate all config files"
    )
    validate_parser.set_defaults(func=validate_challenges)

    generate_parser = subparsers.add_parser("generate", help="generate challenge files")
    generate_parser.set_defaults(func=generate_files)

    clean_parser = subparsers.add_parser(
        "clean", help="clean generated challenge files"
    )
    clean_parser.set_defaults(func=clean_files)

    upload_parser = subparsers.add_parser("upload", help="upload all challenges")
    upload_parser.add_argument("url", help="base url of the CTFd instance")
    upload_parser.add_argument(
        "--token", "-t", required=True, help="token for the admin user"
    )
    upload_parser.set_defaults(func=upload_challenges)

    upgrade_parser = subparsers.add_parser("upgrade", help="upgrade ctftool")
    upgrade_parser.set_defaults(func=upgrade)

    args = parser.parse_args()
    if hasattr(args, "func"):
        return args.func(args)
    else:
        parser.print_help()

    return True


def list_challenges(args):
    cache = {}
    for challenge in Challenge.load_all(True):
        if challenge.category not in cache:
            cache[challenge.category] = []
        cache[challenge.category].append(challenge)

    for category, challenges in cache.items():
        for challenge in challenges:
            if challenge.error is not None:
                continue

            print(f"[{challenge.category}] ", end="")
            print(f"{Style.BRIGHT}{challenge.name}{Style.RESET_ALL} ", end="")
            print(f"{Fore.LIGHTBLACK_EX}- {challenge.path}")
            if args.verbose:
                INDENT = "\n\t\t"
                description = INDENT + challenge.description.replace("\n", INDENT)

                print(f"\tdescription: {description}")
                print(f"\tpoints: {challenge.points}")
                print(f"\tflags: {challenge.flags}")
                print(f"\tfiles: {challenge.files}")

    return True


def validate_challenges(args):
    success = True

    existing_names = set()
    existing_displays = set()

    for challenge in Challenge.load_all(False):
        print(challenge.path, end="")

        failed = False

        def fail(message):
            nonlocal failed, success
            failed = True
            success = False
            print(f"\n{Fore.RED}✗{Style.RESET_ALL} {message}", end="")

        NAME_REGEX = "^[a-z0-9-_]+$"

        if challenge.error is not None:
            fail(f"challenge parse error ({challenge.error})")
        else:
            if not challenge.name:
                fail("challenge 'name' must not be empty")
            elif not re.match(NAME_REGEX, challenge.name):
                fail(f'challenge \'name\' does not match regex "{NAME_REGEX}"')
            elif challenge.name in existing_names:
                fail("challenge 'name' must not be a duplicate")
            else:
                existing_names.add(challenge.name)

            if not challenge.display:
                fail("challenge 'display' must not be empty")
            elif challenge.display in existing_displays:
                fail("challenge 'display' must not be a duplicate")
            else:
                existing_displays.add(challenge.display)

            if not challenge.category:
                fail("challenge 'category' must not be empty")

            for filename in challenge.files:
                if filename in challenge.generate:
                    # generated files may not exist at time of validation
                    continue

                filename_relative = os.path.join(
                    os.path.dirname(challenge.path), filename
                )
                if not os.path.exists(filename_relative):
                    fail(f'challenge file "{filename}" does not exist')

            for hint in challenge.hints:
                if not isinstance(hint, dict):
                    fail("challenge hint is not a map")
                elif "text" not in hint:
                    fail("challenge hint does not have text")
                elif "cost" not in hint:
                    fail("challenge hint does not have a cost")

            if len(challenge.flags) == 0:
                fail("challenge must have at least 1 flag")
            for flag in challenge.flags:
                starts = flag.startswith('/')
                ends = flag.endswith('/')
                if starts and not ends:
                    fail("challenge flag invalid regex: starts with '/' but does not end with '/'")
                if not starts and ends:
                    fail("challenge flag invalid regex: ends with '/' but does not start with '/'")

        if failed:
            print()
        else:
            print(f" {Fore.GREEN}✔{Style.RESET_ALL}")

    return success


def generate_files(args):
    success = True

    for challenge in Challenge.load_all(False):
        for filename, command in challenge.generate.items():
            cwd = os.path.dirname(challenge.path)

            try:
                subprocess.run(command, shell=True, check=True, cwd=cwd)
            except subprocess.CalledProcessError:
                print(f"failed to generate {filename} {Fore.RED}✗{Style.RESET_ALL}")
                success = False
                raise

            if not os.path.exists(os.path.join(cwd, filename)):
                print(f"did not generate {filename} {Fore.RED}✗{Style.RESET_ALL}")
                success = False
            else:
                print(f"generated {filename} {Fore.GREEN}✔{Style.RESET_ALL}")

    return success


def clean_files(args):
    for challenge in Challenge.load_all(False):
        for filename in challenge.generate.keys():
            cwd = os.path.dirname(challenge.path)
            try:
                os.remove(os.path.join(cwd, filename))
            except FileNotFoundError:
                pass


def upload_challenges(args):
    ctfd = CTFd(args.url, args.token)
    success = True

    online = {data["name"]: data for data in ctfd.list()}
    challenge_data = {}

    # upload challenges
    for challenge in Challenge.load_all():
        print(challenge.path, end="")
        try:
            if challenge.display in online:
                ctfd.reupload(online[challenge.display]["id"], challenge)
                print(f"{Fore.YELLOW} ~")
            else:
                ctfd.upload(challenge)
                print(f"{Fore.GREEN} ✓")
        except Exception as e:
            success = False
            print(f"{Fore.RED} ✗ {e}")
            continue

        challenge_data[challenge.display] = challenge
        online = {data["name"]: data for data in ctfd.list()}

    # apply requirements
    for challenge_name, data in online.items():
        challenge = challenge_data[challenge_name]
        ctfd.requirements(data["id"], challenge, online)

    return success


def upgrade(args):
    # download new code
    source_code = requests.get(UPSTREAM).text

    # write code
    path = os.path.realpath(__file__)
    with open(path, "w") as ctftool:
        ctftool.write(source_code)


class Challenge:
    """
    Interface to the challenge files and their contained data.
    """

    def __init__(
        self,
        name: str,
        display: str,
        category: str,
        path: Optional[str],
        description: str = "",
        points: int = 0,
        flags: List[str] = None,
        files: List[str] = None,
        hints: List[Dict[str, Any]] = None,
        generate: Dict[str, str] = None,
        requirements: List[str] = None,
        deploy: "Deploy" = None,
    ):
        self.name = name
        self.display = display
        self.category = category
        self.path = path
        self.description = description
        self.points = points
        self.flags = flags or []
        self.files = files or []
        self.hints = hints or []
        self.generate = generate or {}
        self.requirements = requirements or []
        self.deploy = deploy

        self.error: Optional[Exception] = None

    @staticmethod
    def load_all(suppress_errors: bool = False) -> Iterable["Challenge"]:
        globpath = "challenges/**/challenge.*"
        paths = glob.glob(globpath, recursive=True)

        for path in paths:
            yield Challenge.load(path, suppress_errors)

    @staticmethod
    def load(filename: str, suppress_errors: bool = False) -> "Challenge":
        try:
            return Challenge._load(filename)
        except Exception as e:
            if suppress_errors:
                challenge = Challenge("", "", filename)
                challenge.error = e
                return challenge
            else:
                raise

    @staticmethod
    def _load(filename: str) -> "Challenge":
        with open(filename) as f:
            ext = os.path.splitext(filename)[-1]
            if ext == ".yaml" or ext == ".yml":
                data = yaml.safe_load(f)
            elif ext == ".json":
                data = json.load(f)
            else:
                raise ChallengeLoadError(f'unknown file extension "{ext}"')

        chal = Challenge._load_dict(data)
        chal.path = filename
        return chal

    @staticmethod
    def _load_dict(data: Dict[str, Any]) -> "Challenge":
        return Challenge(
            name=data.get("name", ""),
            display=data.get("display", ""),
            category=data.get("category", ""),
            path=None,
            description=data.get("description", ""),
            points=data.get("points", 0),
            flags=data.get("flags", []),
            files=data.get("files", []),
            hints=data.get("hints", []),
            generate=data.get("generate", {}),
            requirements=data.get("requirements", []),
            deploy=Deploy._load_dict(data.get("deploy", {})),
        )


class Deploy:
    def __init__(self, docker: bool = False, env: List[str] = None, ports: List["Port"] = None):
        self.docker = docker
        self.env = env if env else []
        self.ports = ports if ports else []

    @staticmethod
    def _load_dict(data: Dict[str, Any]) -> "Deploy":
        return Deploy(
            docker=data.get("docker", False),
            env=data.get("env", []),
            ports=[Port._load_dict(port) for port in data.get("ports", [])],
        )


class Port:
    def __init__(self, internal: int, external: int, protocol: str = "tcp"):
        self.internal = internal
        self.external = external
        self.protocol = protocol

    @staticmethod
    def _load_dict(data: Dict[str, Any]) -> "Port":
        return Port(
            internal=data.get("internal", 0),
            external=data.get("external", 0),
            protocol=data.get("protocol", "tcp"),
        )

    def __repr__(self) -> str:
        return f"<Port {self.external}:{self.internal}/{self.protocol}>"

    def __str__(self) -> str:
        return repr(self)


class ChallengeLoadError(RuntimeError):
    pass


class CTFd:
    """
    Client for CTFd server.

    This has been tested with CTFd 3.0.0 on API v1 and should continue
    to work in the future, as long as the API doesn't change too much.
    """

    def __init__(self, url: str, token: str):
        self.base = url
        self.session = requests.Session()

        self.session.headers.update(
            {"Authorization": f"Token {token}",}
        )

    def list(self) -> List[Any]:
        resp = self.session.get(f"{self.base}/api/v1/challenges?view=admin", json={})
        resp.raise_for_status()
        return resp.json()["data"]

    def upload(self, challenge: Challenge) -> int:
        # create challenge
        data = {
            "name": challenge.display,
            "category": challenge.category,
            "state": "visible",
            "value": challenge.points,
            "type": "standard",
            "description": challenge.description,
        }
        resp = self.session.post(f"{self.base}/api/v1/challenges", json=data)
        resp.raise_for_status()
        resp_data = resp.json()
        challenge_id = int(resp_data["data"]["id"])

        self._upload_parts(challenge_id, challenge)

        return challenge_id

    def requirements(
        self, challenge_id: int, challenge: Challenge, online: Dict[str, Any],
    ):
        # determine the requirement ids
        requirement_ids = []
        for req in challenge.requirements:
            requirement_ids.append(online[req]["id"])

        # patch the requirements
        if requirement_ids:
            data = {"requirements": {"prerequisites": requirement_ids}}
            resp = self.session.patch(
                f"{self.base}/api/v1/challenges/{challenge_id}", json=data,
            )
            resp.raise_for_status()

    def reupload(self, challenge_id: int, challenge: Challenge) -> int:
        # patch challenge
        data = {
            "name": challenge.display,
            "category": challenge.category,
            "state": "visible",
            "value": challenge.points,
            "type": "standard",
            "description": challenge.description,
        }
        resp = self.session.patch(
            f"{self.base}/api/v1/challenges/{challenge_id}", json=data,
        )
        resp.raise_for_status()
        resp_data = resp.json()

        self._remove_parts(challenge_id, challenge)
        self._upload_parts(challenge_id, challenge)

        return challenge_id

    def _upload_parts(self, challenge_id: int, challenge: Challenge):
        # add challenge flags
        for flag in challenge.flags:
            if flag.startswith("/") and flag.endswith("/"):
                data = {
                    "challenge": challenge_id,
                    "content": flag[1:-1],
                    "type": "regex",
                }
            else:
                data = {"challenge": challenge_id, "content": flag, "type": "static"}

            resp = self.session.post(f"{self.base}/api/v1/flags", json=data)
            resp.raise_for_status()

        # add challenge hints
        for hint in challenge.hints:
            if not isinstance(hint, dict):
                continue
            if "text" not in hint or "cost" not in hint:
                continue

            data = {
                "content": hint["text"],
                "cost": hint["cost"],
                "challenge": challenge_id,
            }
            resp = self.session.post(f"{self.base}/api/v1/hints", json=data)
            resp.raise_for_status()

        # upload challenge files
        if challenge.path:
            for filename in challenge.files:
                fullfilename = os.path.join(os.path.dirname(challenge.path), filename)
                data = {
                    "challenge": challenge_id,
                    "type": "challenge",
                }
                files = {"file": (filename, open(fullfilename, "rb"))}

                resp = self.session.post(
                    f"{self.base}/api/v1/files", data=data, files=files,
                )
                resp.raise_for_status()

    def _remove_parts(self, challenge_id: int, challenge: Challenge):
        # remove challenge flags
        resp = self.session.get(f"{self.base}/api/v1/challenges/{challenge_id}/flags")
        resp.raise_for_status()
        online_flags = resp.json()["data"]
        for flag in online_flags:
            self.session.delete(
                f"{self.base}/api/v1/flags/{flag['id']}"
            ).raise_for_status()

        # remove challenge hints
        resp = self.session.get(f"{self.base}/api/v1/challenges/{challenge_id}/hints")
        resp.raise_for_status()
        online_hints = resp.json()["data"]
        for hint in online_hints:
            self.session.delete(
                f"{self.base}/api/v1/hints/{hint['id']}"
            ).raise_for_status()

        # remove challenge files
        resp = self.session.get(f"{self.base}/api/v1/challenges/{challenge_id}/files")
        resp.raise_for_status()
        online_files = resp.json()["data"]
        for file in online_files:
            self.session.delete(
                f"{self.base}/api/v1/files/{file['id']}"
            ).raise_for_status()


if __name__ == "__main__":
    # run with colorama
    colorama.init(autoreset=True)
    try:
        success = main()
    except Exception:
        traceback.print_exc()
        success = False
    finally:
        colorama.deinit()

    if success is None or success:
        sys.exit(0)
    else:
        sys.exit(1)
