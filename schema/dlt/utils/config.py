
from dynaconf import Dynaconf

settings = Dynaconf(
    envvar_prefix='EyeOnData_',
    settings_files=['EyeOnData.toml'],
)
