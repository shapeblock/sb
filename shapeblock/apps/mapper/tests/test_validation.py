import unittest
from apps.mapper.validator import validate_yaml


class TestYAMLValidation(unittest.TestCase):
    def test_valid_yaml(self):
        yaml_string = """
        name: 'test-123'
        type: 'php'
        version: '8.1'
        # ... (other properties)
        """
        validated_data, validation_errors = validate_yaml(yaml_string)
        self.assertIsNotNone(validated_data)
        self.assertIsNone(validation_errors)

    def test_invalid_yaml(self):
        yaml_string = """
        invalid_yaml: true
        """
        validated_data, validation_errors = validate_yaml(yaml_string)
        self.assertIsNone(validated_data)
        self.assertIsNotNone(validation_errors)

    def test_invalid_version(self):
        yaml_string = """
        name: 'test-123'
        type: 'php'
        version: '9.0'
        # ... (other properties)
        """
        validated_data, validation_errors = validate_yaml(yaml_string)
        self.assertIsNone(validated_data)
        self.assertIsNotNone(validation_errors)

    # Add more test cases as needed...


if __name__ == "__main__":
    unittest.main()
