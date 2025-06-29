import re
from sqlalchemy import (
    Column, String, Integer, MetaData, Table, inspect as sqla_inspect
)
from app.models.database import Base, engine


def clean_client_name(client_name: str) -> str:
    """Cleans the client name to be suitable for a table name prefix."""
    return re.sub(r'\W+', '', client_name.replace(' ', '_')).upper()


def clean_system_name(system_name: str) -> str:
    """Cleans the client name to be suitable for a table name prefix."""
    return re.sub(r'\W+', '', system_name.replace(' ', '_')).upper()


def clean_system_release_versionInfo(system_release_version: str) -> str:
    """Cleans the client name to be suitable for a table name prefix."""
    return re.sub(r'\W+', '', system_release_version.replace(' ', '_')).upper()




def get_lice_data_tablename(client_name: str,system_name:str) -> str:
    client = clean_client_name(client_name)
    system= clean_system_name(system_name)
    return f"Z_FUE_{client}_{system}_ROLE_OBJ_LICENSE_INFO"

def get_auth_data_tablename(client_name: str,system_name:str) -> str:
    client = clean_client_name(client_name)
    system = clean_system_name(system_name)
    return f"Z_FUE_{client}_{system}_ROLE_AUTH_OBJ_DATA"

def get_role_fiori_data_tablename(client_name: str,system_name:str) -> str:
    client = clean_client_name(client_name)
    system= clean_system_name(system_name)
    return f"Z_FUE_{client}_{system}_ROLE_FIORI_DATA"

def get_role_master_derived_data_tablename(client_name: str,system_name:str) -> str:
    client = clean_client_name(client_name)
    system = clean_system_name(system_name)
    return f"Z_FUE_{client}_{system}_ROLE_MASTER_DERVI_DATA"

def get_user_data_tablename(client_name: str,system_name:str) -> str:
    client = clean_client_name(client_name)
    system= clean_system_name(system_name)
    return f"Z_FUE_{client}_{system}_USER_DATA"

def get_user_role_data_tablename(client_name: str,system_name:str) -> str:
    client = clean_client_name(client_name)
    system = clean_system_name(system_name)
    return f"Z_FUE_{client}_{system}_USER_ROLE_DATA"



class _BaseLiceData:
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    AGR_NAME = Column(String, index=True)
    OBJECT = Column(String, nullable=False)
    TTEXT = Column(String)
    FIELD = Column(String)
    LOW = Column(String)
    HIGH = Column(String)
    CLASSIF_S4 = Column(String)
    AGR_TEXT = Column(String)
    AGR_CLASSIF = Column(String)
    AGR_RATIO = Column(String)
    AGR_OBJECTS = Column(String)
    AGR_USERS = Column(String)

class _BaseAuthData:
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    AGR_NAME = Column(String, nullable=False, index=True)
    OBJECT = Column(String, nullable=False)
    AUTH_NAME = Column(String, nullable=False)
    FIELD_NAME = Column(String, nullable=False)
    AUTH_VALUE_LOW = Column(String)
    AUTH_VALUE_HIGH = Column(String)

class _BaseFioriRoleData:
    id= Column(Integer, primary_key=True, index=True, autoincrement=True)
    ROLE= Column(String, nullable=False, index=True)
    ROLE_DESCRIPTION = Column(String)
    TILE_TARGET_MAPPING_MATCHING_TEXT=Column(String)
    SEMANTIC_OBJECT=Column(String)
    ACTION=Column(String)
    TITLE_SUBTITLE_INFORMATION=Column(String)
    APPLICATION_TYPE=Column(String)
    APPLICATION_RESOURCES=Column(String)
    SAP_FIORI_ID=Column(String)
    APPLICATION_COMPONENT_ID=Column(String)
    ODATA_SERVICE_NAME=Column(String)
    CATALOG_ID=Column(String)
    CATALOG_TITLE=Column(String)


class _RoleMasterDerviData:
    id=Column(Integer, primary_key=True, index=True, autoincrement=True)
    DERIVED_ROLE =Column(String)
    MASTER_ROLE=Column(String)
    TEXT=Column(String)

class _UserData:
    id= Column("id", Integer, primary_key=True, index=True, autoincrement=True)
    USER=Column("USER", String, nullable=False, index=True) # Explicitly named
    FULL_NAME=Column("FULL_NAME", String) # Explicitly named
    ID=Column("ID", String) # Already correct
    CURRENT_CLASSIFICATION=Column("CURRENT_CLASSIFICATION", String) # Explicitly named
    TARGET_CLASSIFICATION=Column("TARGET_CLASSIFICATION", String) # Explicitly named
    RATIO=Column("RATIO", String) # Explicitly named
    REF_USER=Column("REF_USER", String) # Explicitly named
    USER_GROUP=Column("USER_GROUP", String) # Already correct
    LAST_LOGON=Column("LAST_LOGON", String) # Explicitly named
    COUNT=Column("COUNT", String) # Explicitly named



class _UserRoleData:
    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    ROLE= Column(String, nullable=False, index=True)
    USER_NAME=Column(String, nullable=False)

_dynamic_models_cache = {}

def create_lice_data_model(client_name: str,system_name:str):
    table_name = get_lice_data_tablename(client_name,system_name)
    if table_name in _dynamic_models_cache:
        return _dynamic_models_cache[table_name]

    DynamicLiceDataModel = type(
        f"Z_FUE_{clean_client_name(client_name)}_{clean_system_name(system_name)}LiceData",
        (_BaseLiceData, Base),
        {"__tablename__": table_name, "__table_args__": {'extend_existing': True}}
    )
    _dynamic_models_cache[table_name] = DynamicLiceDataModel
    return DynamicLiceDataModel

def create_auth_data_model(client_name: str,system_name:str):
    table_name = get_auth_data_tablename(client_name,system_name)
    if table_name in _dynamic_models_cache:
        return _dynamic_models_cache[table_name]

    DynamicAuthDataModel = type(
        f"Z_FUE_{clean_client_name(client_name)}_{clean_system_name(system_name)}AuthData",
        (_BaseAuthData, Base),
        {"__tablename__": table_name, "__table_args__": {'extend_existing': True}}
    )
    _dynamic_models_cache[table_name] = DynamicAuthDataModel
    return DynamicAuthDataModel

def create_role_fiori_data_model(client_name: str,system_name:str):
    table_name = get_role_fiori_data_tablename(client_name,system_name)
    if table_name in _dynamic_models_cache:
        return _dynamic_models_cache[table_name]

    DynamicRoleFioriDataModel = type(
        f"Z_FUE_{clean_client_name(client_name)}_{clean_system_name(system_name)}RoleFioriData",
        (_BaseFioriRoleData, Base),
        {"__tablename__": table_name, "__table_args__": {'extend_existing': True}}
    )
    _dynamic_models_cache[table_name] = DynamicRoleFioriDataModel
    return DynamicRoleFioriDataModel

def create_role_master_derived_data(client_name: str,system_name:str):
    table_name = get_role_master_derived_data_tablename(client_name,system_name)
    if table_name in _dynamic_models_cache:
        return _dynamic_models_cache[table_name]

    DynamicMasterDerivedDataModel = type(
        f"Z_FUE_{clean_client_name(client_name)}_{clean_system_name(system_name)}MasterDerivedData",
        (_RoleMasterDerviData, Base),
        {"__tablename__": table_name, "__table_args__": {'extend_existing': True}}
    )
    _dynamic_models_cache[table_name] = DynamicMasterDerivedDataModel
    return DynamicMasterDerivedDataModel

def create_user_data(client_name: str,system_name:str):
    table_name = get_user_data_tablename(client_name,system_name)
    if table_name in _dynamic_models_cache:
        return _dynamic_models_cache[table_name]

    DynamicUserDataModel = type(
        f"Z_FUE_{clean_client_name(client_name)}_{clean_system_name(system_name)}UserData",
        (_UserData, Base),
        {"__tablename__": table_name, "__table_args__": {'extend_existing': True}}
    )
    _dynamic_models_cache[table_name] = DynamicUserDataModel
    return DynamicUserDataModel

def create_user_role_data(client_name: str,system_name:str):
    table_name = get_user_role_data_tablename(client_name,system_name)
    if table_name in _dynamic_models_cache:
        return _dynamic_models_cache[table_name]

    DynamicUserRoleDataModel = type(
        f"Z_FUE_{clean_client_name(client_name)}_{clean_system_name(system_name)}UserRoleData",
        (_UserRoleData, Base),
        {"__tablename__": table_name, "__table_args__": {'extend_existing': True}}
    )
    _dynamic_models_cache[table_name] = DynamicUserRoleDataModel
    return DynamicUserRoleDataModel

def ensure_table_exists(db_engine, model_class):
    inspector = sqla_inspect(db_engine)
    table_name = model_class.__tablename__
    if not inspector.has_table(table_name):
        print(f"Table '{table_name}' not found. Creating...")
        try:
            model_class.__table__.create(bind=db_engine)
            print(f"Table '{table_name}' created.")
        except Exception as e:
            print(f"Error creating table {table_name}: {e}")
            raise
    else:
        print(f"Table '{table_name}' already exists.")


