import os
from typing import Dict

import yaml
from jsonschema.validators import exceptions, Draft202012Validator

from django.template.loader import render_to_string

schema_yaml = os.path.join(os.path.dirname(__file__), "schema.yaml")

schema = yaml.safe_load(open(schema_yaml).read())

versions_yaml = os.path.join(os.path.dirname(__file__), "versions.yaml")

version_enum = yaml.safe_load(open(versions_yaml).read())


def validate_yaml(yaml_str):
    validation_errors = []
    try:
        yaml_data = yaml.safe_load(yaml_str)
        validator = Draft202012Validator(schema)
        validator.validate(yaml_data)
        if (
            "type" in yaml_data
            and "version" in yaml_data
            and yaml_data["type"] in version_enum.keys()
        ):
            if yaml_data["version"] not in str(version_enum[yaml_data["type"]]):
                version_mismatch_error = f"Invalid version for {yaml_data['type']}. Only the following versions are supported: {version_enum[yaml_data['type']]}"
                validation_errors.append(version_mismatch_error)
                raise exceptions.ValidationError(version_mismatch_error)

        return yaml_data, None
    except exceptions.ValidationError as e:
        for error in validator.iter_errors(yaml_data):
            validation_errors.append(error.message)
        return None, validation_errors
    except yaml.YAMLError as e:
        return None, ["YAML parsing error: " + str(e)]


def generate_helm_values(sb_yml: Dict) -> str:
    pass


""" Usage:
    
# Example YAML string
yaml_string = '''
name: hello-w
type: php
version: "8.11"
'''

validated_data, validation_errors = validate_yaml(yaml_string)

if validation_errors:
    print("Validation errors:")
    for error in validation_errors:
        print(error)
elif validated_data is not None:
    print("Validated YAML data:", validated_data)

"""
