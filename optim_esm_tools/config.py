"""Shared common methods for reprocessing, not useful in itself"""
from optim_esm_tools.utils import root_folder
import configparser
import logging
import os

if 'OPTIM_ESM_CONFIG' in os.environ:
    config_path = os.environ['OPTIM_ESM_CONFIG']
else:
    _warn_later = True
    config_path = os.path.join(root_folder, 'optim_esm_tools', 'optim_esm_conf.ini')

config = configparser.ConfigParser()
config.sections()
config.read(config_path)

_logger = {}


def get_logger(name='oet'):
    if name not in _logger:
        logging.basicConfig(
            level=getattr(logging, config['log']['logging_level'].upper()),
            format=(
                '%(asctime)s '
                '| %(name)-12s '
                '| %(levelname)-8s '
                '| %(message)s '
                '| %(funcName)s (l. %(lineno)d)'
            ),
            datefmt='%m-%d %H:%M',
        )

        log = logging.getLogger(name)
        _logger[name] = log
    return _logger[name]


if _warn_later:
    get_logger().info(
        f'Using {config_path}-config. Overwrite by setting "OPTIM_ESM_CONFIG" '
        f'as an environment variable'
    )
