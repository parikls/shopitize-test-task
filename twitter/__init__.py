from logging.config import dictConfig

logging_config = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'simple': {
            'format': '[%(asctime)s - %(name)s - %(levelname)s ] - %(message)s'
        }
    },
    'handlers': {
        'console_handler': {
            'level': 'DEBUG',
            'class': 'logging.StreamHandler',
            'formatter': 'simple',
        },
    },
    'loggers': {
        'twitter': {
            'handlers': ['console_handler'],
            'level': 'WARNING',
            'propagate': True,
        },
    },
}

dictConfig(logging_config)
