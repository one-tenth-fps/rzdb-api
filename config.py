import yaml

with open("config.yaml", encoding="utf8") as f:
    config = yaml.safe_load(f)

BAD_REQUEST_STATUS = config["app"]["ERROR_STATUS"]
OK_STATUS = config["app"]["OK_STATUS"]
CAR_SEARCH_RADIUS_LIMIT = config["app"]["CAR_SEARCH_RADIUS_LIMIT"]
REQUEST_ID_LENGTH_LIMIT = config["app"]["REQUEST_ID_LENGTH_LIMIT"]
DEBUG = config["app"]["DEBUG"]

DB_DRIVER = config["db"]["driver"]
DB_SERVER = config["db"]["server"]
DB_USER = config["db"]["user"]
DB_PASSWORD = config["db"]["password"]
DB_DATABASE = config["db"]["database"]
DB_ENCRYPT = config["db"]["encrypt"]
DB_CONNECTION_STRING = f"DRIVER={DB_DRIVER};SERVER={DB_SERVER};DATABASE={DB_DATABASE};UID={DB_USER};PWD={DB_PASSWORD}"\
                       f"{';Encrypt=YES;TrustServerCertificate=YES' if DB_ENCRYPT else ''}"
