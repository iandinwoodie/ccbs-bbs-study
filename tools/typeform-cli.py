#!/usr/bin/env python3

# Standard library imports
import argparse
import os
import json
import pathlib

# Third-party library imports
import typeform


class Typeform:

    TITLE = "Dogs & Children Survey"

    def __init__(self, api_key: str, forms_dir: pathlib.Path, data_dir: pathlib.Path):
        self.tf = typeform.Typeform(token=api_key)
        if not self.tf:
            raise ValueError("Failed to create Typeform client.")
        self.forms_dir = forms_dir
        self.data_dir = data_dir

    def _get_form_id(self) -> tuple[str, str]:
        """Returns a dictionary of form titles and their IDs."""
        pages : int = self.tf.forms.list().get("page_count")
        for i in range(pages):
            forms : dict = self.tf.forms.list(page=i + 1)
            for form in forms["items"]:
                if form.get("title") == self.TITLE:
                    return form.get("title"), form.get("id")
        raise RuntimeError(f"Form with title '{self.TITLE}' not found.")

    def _sanitize_responses(self, responses: dict) -> dict:
        """Sanitizes the responses to remove any PII."""
        owner_ids = {}
        for response in responses.get("items"):
            for answer in response.get("answers"):
                if answer.get("type") == "email":
                    owner_ids[answer.get("email")] = response.get("response_id")
                    answer["email"] = response.get("response_id")
        return responses

    def pull_forms(self):
        print("Pulling forms from Typeform...")
        # Create the forms directory if it doesn't exist.
        if not self.forms_dir.exists():
            self.forms_dir.mkdir(parents=True)

        title, id = self._get_form_id()
        print(f"Pulling form: {title}")
        form : dict = self.tf.forms.get(uid=id)
        form_json = json.dumps(form, indent=2)
        mf_title = to_machine_friendly_title(title)
        form_path = self.forms_dir / f"{mf_title}.json"
        with open(form_path, "w") as f:
            f.write(form_json)

    def pull_responses(self):
        print("Pulling responses from Typeform...")

        title, id = self._get_form_id()
        print(f"Pulling responses for form: {title}")
        responses : dict = self.tf.responses.list(uid=id, pageSize=1000)
        cnt = responses.get("total_items")
        if cnt == 0:
            print(f"No responses to pull.")
        elif cnt >= 1000 or responses.get("page_count") > 1:
            raise RuntimeError("1000 or more responses; requires pagination support.")
        else:
            print(f"Pulling {cnt} responses.")

        # Sanitize the responses to remove any PII.
        responses = self._sanitize_responses(responses)

        # Create the data directory if it doesn't exist.
        if not self.data_dir.exists():
            self.data_dir.mkdir(parents=True)

        if len(responses.items()) > 0:
            response_json = json.dumps(responses, indent=2)
            mf_title = to_machine_friendly_title(title)
            response_path = self.data_dir / f"{mf_title}.json"
            with open(response_path, "w") as f:
                f.write(response_json)


def get_script_dir() -> pathlib.Path:
    """Returns the directory of the current script."""
    return pathlib.Path(os.path.dirname(os.path.abspath(__file__)))


def get_forms_dir() -> pathlib.Path:
    """Returns the directory where forms are stored."""
    return get_script_dir().parent / "forms"


def get_data_dir() -> pathlib.Path:
    """Returns the directory where data is stored."""
    return get_script_dir().parent / "data"


def to_machine_friendly_title(title : str) -> str:
    """Returns a machine-friendly version of the given title."""
    replacements = {
        " ": "-",
        "&": "and",
    }
    return title.translate(str.maketrans(replacements)).lower()


def main():
    parser = argparse.ArgumentParser(description="Typeform CLI")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--pull-forms", action="store_true", help="Pull forms from Typeform")
    group.add_argument("--pull-responses", action="store_true", help="Pull responses from Typeform")
    args = parser.parse_args()

    api_key = os.getenv("TYPEFORM_API_KEY")
    if not api_key:
        raise ValueError("TYPEFORM_API_KEY environment variable is not set.")
    tf = Typeform(api_key=api_key, forms_dir=get_forms_dir(), data_dir=get_data_dir())

    if args.pull_forms:
        tf.pull_forms()
    elif args.pull_responses:
        tf.pull_responses()
    else:
        print("No action specified. Use --help for more information.")


if __name__ == "__main__":
    main()
