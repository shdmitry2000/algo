from configuration import (
    Configuration,
)


def prepare_conf(tmp_path):
    """
    Prepare configuration file for tests
    :param tmp_path: pytest tmp_path fixture
    :return: configuration for tests
    """
    test_config = dict(
        keystore_location=str(tmp_path)
    )
    test_config = Configuration(
        config_dir=str(tmp_path),
        initial_config=test_config
    )
    return test_config.load_configuration()
