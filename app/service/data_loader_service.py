import xml.etree.ElementTree as ET
import csv
from io import BytesIO
from sqlalchemy.orm import Session
from app.core.logger import logger
from app.models.dynamic_models import (
    create_lice_data_model,
    create_auth_data_model,
    ensure_table_exists, create_role_fiori_data_model, create_role_master_derived_data, create_user_role_data,
    create_user_data
)
from app.models.database import engine

class DataLoaderError(Exception):
    pass

async def load_lice_data_from_xml_upload(db: Session, xml_file, client_name: str, system_name: str):
    if not xml_file:
        logger.info(f"Skipping XML data load for client: {client_name}, system: {system_name} as no file was provided.")
        print(f"Skipping XML data load for client: {client_name}, system: {system_name} as no file was provided.")
        return {"message": "No XML file provided, skipping load.", "table_name": None, "records_loaded": 0}

    logger.info(f"Starting XML data load for client: {client_name}, system: {system_name}")

    DynamicLiceModel = create_lice_data_model(client_name, system_name)
    table_name = DynamicLiceModel.__tablename__
    ensure_table_exists(engine, DynamicLiceModel)

    try:
        deleted_count = db.query(DynamicLiceModel).delete()
        logger.info(f"Truncated (deleted) {deleted_count} rows from {table_name}.")
        print(f"Truncated (deleted) {deleted_count} rows from {table_name}.")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to truncate table {table_name}: {e}")
        raise DataLoaderError(f"Failed to truncate table {table_name}: {e}")

    try:
        xml_content = xml_file.read()
        tree = ET.parse(BytesIO(xml_content))
        root = tree.getroot()
        namespaces = {'asx': 'http://www.sap.com/abapxml'}
        items = root.findall('.//asx:values/DOWNLOAD/item', namespaces)
        if not items:
            logger.warning("No <item> elements found in XML.")
            raise DataLoaderError("No <item> elements found in XML.")

        roles_info = {}
        objects_to_load = []
        for item in items:
            agr_name = item.findtext('AGR_NAME', '')
            auth_obj = item.findtext('OBJECT', '')
            if not auth_obj:
                agr_classif_check = item.findtext('AGR_CLASSIF')
                if agr_name and agr_classif_check is not None:
                    roles_info[agr_name] = {
                        'AGR_TEXT': item.findtext('AGR_TEXT', ''),
                        'AGR_CLASSIF': item.findtext('AGR_CLASSIF', ''),
                        'AGR_RATIO': item.findtext('AGR_RATIO', ''),
                        'AGR_OBJECTS': item.findtext('AGR_OBJECTS', '0'),
                        'AGR_USERS': item.findtext('AGR_USERS', '0')
                    }
            else:
                role_specific_info = roles_info.get(agr_name, {})
                lice_data_obj = DynamicLiceModel(
                    AGR_NAME=agr_name, OBJECT=auth_obj,
                    TTEXT=item.findtext('TTEXT', ''), FIELD=item.findtext('FIELD', ''),
                    LOW=item.findtext('LOW', ''), HIGH=item.findtext('HIGH', ''),
                    CLASSIF_S4=item.findtext('CLASSIF_S4', ''),
                    AGR_TEXT=role_specific_info.get('AGR_TEXT', item.findtext('AGR_TEXT', '')),
                    AGR_CLASSIF=role_specific_info.get('AGR_CLASSIF', item.findtext('AGR_CLASSIF', '')),
                    AGR_RATIO=role_specific_info.get('AGR_RATIO', item.findtext('AGR_RATIO', '')),
                    AGR_OBJECTS=role_specific_info.get('AGR_OBJECTS', item.findtext('AGR_OBJECTS', '0')),
                    AGR_USERS=role_specific_info.get('AGR_USERS', item.findtext('AGR_USERS', '0'))
                )
                objects_to_load.append(lice_data_obj)

        if not objects_to_load:
            logger.warning("No valid object data found in XML.")
            raise DataLoaderError("No valid object data found.")

        db.add_all(objects_to_load)
        db.commit()
        msg = f"Successfully loaded {len(objects_to_load)} records into {table_name}"
        logger.info(msg)
        print(msg)
        return {"message": msg, "table_name": table_name, "records_loaded": len(objects_to_load)}


    except ET.ParseError as e:
        db.rollback()
        logger.error(f"XML ParseError: {e}", exc_info=True)
        raise DataLoaderError(f"XML ParseError: {e}")

    except Exception as e:
        db.rollback()
        logger.error(f"Failed loading XML data: {e}", exc_info=True)
        raise DataLoaderError(f"Failed loading XML data: {e}")



async def load_auth_data_from_csv_upload(db: Session, csv_file, client_name: str, system_name: str):
    """Parses Role Auth CSV from a file-like object, ensures table exists, truncates, and loads data."""
    if not csv_file:
        logger.info(f"Skipping CSV data load for client: {client_name}, system: {system_name} as no file was provided.")
        print(f"Skipping CSV data load for client: {client_name}, system: {system_name} as no file was provided.")
        return {"message": "No CSV file provided, skipping load.", "table_name": None, "records_loaded": 0}

    logger.info(f"Starting CSV data load for client: {client_name}, system: {system_name}")


    DynamicAuthModel = create_auth_data_model(client_name, system_name) # Pass system_name
    table_name = DynamicAuthModel.__tablename__
    engine = db.bind
    ensure_table_exists(engine, DynamicAuthModel)

    try:
        deleted_count = db.query(DynamicAuthModel).delete()
        logger.info(f"Truncated (deleted) {deleted_count} rows from {table_name}.")
        print(f"Truncated (deleted) {deleted_count} rows from {table_name}.")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to truncate table {table_name}: {e}", exc_info=True)
        raise DataLoaderError(f"Failed to truncate table {table_name}: {e}")

    objects_to_load = []
    try:
        csv_content = csv_file.read()
        try:
            csv_text = BytesIO(csv_content).read().decode('utf-8-sig')
        except UnicodeDecodeError:
            try:
                csv_text = BytesIO(csv_content).read().decode('latin-1')
            except UnicodeDecodeError:
                csv_text = BytesIO(csv_content).read().decode('cp1252')
        csv_reader = csv.reader(csv_text.splitlines())
        headers = ['agr_name', 'object', 'auth_name', 'field_name', 'auth_value_low', 'auth_value_high']
        next(csv_reader)



        field_map = {
            'AGR_NAME': 0,
            'OBJECT': 1,
            'AUTH_NAME': 2,
            'FIELD_NAME': 3,
            'AUTH_VALUE_LOW': 4,
            'AUTH_VALUE_HIGH': 5
        }

        for i, row in enumerate(csv_reader):
            try:
                obj_data = {model_field: row[csv_index]
                            for model_field, csv_index in field_map.items()}
                auth_data_obj = DynamicAuthModel(**obj_data)
                objects_to_load.append(auth_data_obj)
            except IndexError as e:
                logger.error(f"Error processing row {i+2} in CSV data: Not enough columns. Row: {row}")
                print(f"Error processing row {i+2} in CSV data: Not enough columns. Row: {row}")
                raise DataLoaderError(f"Error processing row {i+2}: Not enough columns.")
            except Exception as row_e:
                print(f"Error processing row {i+2} in CSV data: {row_e}")
                print(f"Row data: {row}")
                logger.error(f"Error processing row {i+2} in CSV data: {row_e}")
                raise DataLoaderError(f"Error processing row {i+2}: {row_e}")

        if not objects_to_load:
            logger.warning(f"Warning: No data rows found in CSV data.")
            print(f"Warning: No data rows found in CSV data.")

        db.add_all(objects_to_load)
        db.commit()
        msg = f"Successfully loaded {len(objects_to_load)} records into {table_name}"
        logger.info(msg)
        print(msg)
        return {"message": msg, "table_name": table_name, "records_loaded": len(objects_to_load)}

    except Exception as e:
        db.rollback()
        logger.warning(f"Failed loading CSV data: {e}")
        raise DataLoaderError(f"Failed loading CSV data: {e}")




async def load_role_fiori_map_data_from_csv_upload(db: Session, csv_file, client_name: str, system_name: str):
    """Parses Role Auth CSV from a file-like object, ensures table exists, truncates, and loads data."""
    if not csv_file:
        logger.info(f"Skipping CSV data load for client: {client_name}, system: {system_name} as no file was provided.")
        print(f"Skipping CSV data load for client: {client_name}, system: {system_name} as no file was provided.")
        return {"message": "No CSV file provided, skipping load.", "table_name": None, "records_loaded": 0}

    logger.info(f"Starting CSV data load for client: {client_name}, system: {system_name}")


    DynamicRoleFioriDataModel = create_role_fiori_data_model(client_name, system_name) # Pass system_name
    table_name = DynamicRoleFioriDataModel.__tablename__
    engine = db.bind
    ensure_table_exists(engine, DynamicRoleFioriDataModel)

    try:
        deleted_count = db.query(DynamicRoleFioriDataModel).delete()
        logger.info(f"Truncated (deleted) {deleted_count} rows from {table_name}.")
        print(f"Truncated (deleted) {deleted_count} rows from {table_name}.")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to truncate table {table_name}: {e}", exc_info=True)
        raise DataLoaderError(f"Failed to truncate table {table_name}: {e}")

    objects_to_load = []
    try:
        csv_content = csv_file.read()
        try:
            csv_text = BytesIO(csv_content).read().decode('utf-8-sig')
        except UnicodeDecodeError:
            try:
                csv_text = BytesIO(csv_content).read().decode('latin-1')
            except UnicodeDecodeError:
                csv_text = BytesIO(csv_content).read().decode('cp1252')
        csv_reader = csv.reader(csv_text.splitlines())
        headers = ['role', 'role_description','sematic_object', 'action', 'title_subtitle_information', 'application_type', 'application_resources','sap_fiori_id','tile_title']
        next(csv_reader)


        field_map = {
            'ROLE': 0,
            'ROLE_DESCRIPTION': 1,
            'TILE_TARGET_MAPPING_MATCHING_TEXT': 2,
            'SEMANTIC_OBJECT': 3,
            'ACTION': 4,
            'TITLE_SUBTITLE_INFORMATION': 5,
            'APPLICATION_TYPE': 6,
            'APPLICATION_RESOURCES': 7,
            'SAP_FIORI_ID' :8,
            'APPLICATION_COMPONENT_ID':9,
            'ODATA_SERVICE_NAME' :10,
            'CATALOG_ID' :11,
            'CATALOG_TITLE':12
        }

        for i, row in enumerate(csv_reader):
            try:
                obj_data = {model_field: row[csv_index]
                            for model_field, csv_index in field_map.items()}
                auth_data_obj = DynamicRoleFioriDataModel(**obj_data)
                objects_to_load.append(auth_data_obj)
            except IndexError as e:
                logger.error(f"Error processing row {i+2} in CSV data: Not enough columns. Row: {row}")
                print(f"Error processing row {i+2} in CSV data: Not enough columns. Row: {row}")
                raise DataLoaderError(f"Error processing row {i+2}: Not enough columns.")
            except Exception as row_e:
                print(f"Error processing row {i+2} in CSV data: {row_e}")
                print(f"Row data: {row}")
                logger.error(f"Error processing row {i+2} in CSV data: {row_e}")
                raise DataLoaderError(f"Error processing row {i+2}: {row_e}")

        if not objects_to_load:
            logger.warning(f"Warning: No data rows found in CSV data.")
            print(f"Warning: No data rows found in CSV data.")

        db.add_all(objects_to_load)
        db.commit()
        msg = f"Successfully loaded {len(objects_to_load)} records into {table_name}"
        logger.info(msg)
        print(msg)
        return {"message": msg, "table_name": table_name, "records_loaded": len(objects_to_load)}

    except Exception as e:
        db.rollback()
        logger.warning(f"Failed loading CSV data: {e}")
        raise DataLoaderError(f"Failed loading CSV data: {e}")


async def load_master_derived_role_data_from_csv_upload(db: Session, csv_file, client_name: str, system_name: str):
    """Parses Role Auth CSV from a file-like object, ensures table exists, truncates, and loads data."""
    if not csv_file:
        logger.info(f"Skipping CSV data load for client: {client_name}, system: {system_name} as no file was provided.")
        print(f"Skipping CSV data load for client: {client_name}, system: {system_name} as no file was provided.")
        return {"message": "No CSV file provided, skipping load.", "table_name": None, "records_loaded": 0}

    logger.info(f"Starting CSV data load for client: {client_name}, system: {system_name}")


    DynamicMasterDerivedDataModel = create_role_master_derived_data(client_name, system_name) # Pass system_name
    table_name = DynamicMasterDerivedDataModel.__tablename__
    engine = db.bind
    ensure_table_exists(engine, DynamicMasterDerivedDataModel)

    try:
        deleted_count = db.query(DynamicMasterDerivedDataModel).delete()
        logger.info(f"Truncated (deleted) {deleted_count} rows from {table_name}.")
        print(f"Truncated (deleted) {deleted_count} rows from {table_name}.")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to truncate table {table_name}: {e}", exc_info=True)
        raise DataLoaderError(f"Failed to truncate table {table_name}: {e}")

    objects_to_load = []
    try:
        csv_content = csv_file.read()
        try:
            csv_text = BytesIO(csv_content).read().decode('utf-8-sig')
        except UnicodeDecodeError:
            try:
                csv_text = BytesIO(csv_content).read().decode('latin-1')
            except UnicodeDecodeError:
                csv_text = BytesIO(csv_content).read().decode('cp1252')
        csv_reader = csv.reader(csv_text.splitlines())
        headers = ['derived_role', 'master_role']
        next(csv_reader)
        field_map = {
            'DERIVED_ROLE': 0,
            'MASTER_ROLE': 1
        }

        for i, row in enumerate(csv_reader):
            try:
                obj_data = {model_field: row[csv_index]
                            for model_field, csv_index in field_map.items()}
                auth_data_obj = DynamicMasterDerivedDataModel(**obj_data)
                objects_to_load.append(auth_data_obj)
            except IndexError as e:
                logger.error(f"Error processing row {i+2} in CSV data: Not enough columns. Row: {row}")
                print(f"Error processing row {i+2} in CSV data: Not enough columns. Row: {row}")
                raise DataLoaderError(f"Error processing row {i+2}: Not enough columns.")
            except Exception as row_e:
                print(f"Error processing row {i+2} in CSV data: {row_e}")
                print(f"Row data: {row}")
                logger.error(f"Error processing row {i+2} in CSV data: {row_e}")
                raise DataLoaderError(f"Error processing row {i+2}: {row_e}")

        if not objects_to_load:
            logger.warning(f"Warning: No data rows found in CSV data.")
            print(f"Warning: No data rows found in CSV data.")

        db.add_all(objects_to_load)
        db.commit()
        msg = f"Successfully loaded {len(objects_to_load)} records into {table_name}"
        logger.info(msg)
        print(msg)
        return {"message": msg, "table_name": table_name, "records_loaded": len(objects_to_load)}

    except Exception as e:
        db.rollback()
        logger.warning(f"Failed loading CSV data: {e}")
        raise DataLoaderError(f"Failed loading CSV data: {e}")



async def load_user_role_map_data_from_csv_upload(db: Session, csv_file, client_name: str, system_name: str):
    """Parses Role Auth CSV from a file-like object, ensures table exists, truncates, and loads data."""
    if not csv_file:
        logger.info(f"Skipping CSV data load for client: {client_name}, system: {system_name} as no file was provided.")
        print(f"Skipping CSV data load for client: {client_name}, system: {system_name} as no file was provided.")
        return {"message": "No CSV file provided, skipping load.", "table_name": None, "records_loaded": 0}

    logger.info(f"Starting CSV data load for client: {client_name}, system: {system_name}")

    DynamicUserRoleDataModel = create_user_role_data(client_name, system_name) # Pass system_name
    table_name = DynamicUserRoleDataModel.__tablename__
    engine = db.bind
    ensure_table_exists(engine, DynamicUserRoleDataModel)

    try:
        deleted_count = db.query(DynamicUserRoleDataModel).delete()
        logger.info(f"Truncated (deleted) {deleted_count} rows from {table_name}.")
        print(f"Truncated (deleted) {deleted_count} rows from {table_name}.")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to truncate table {table_name}: {e}", exc_info=True)
        raise DataLoaderError(f"Failed to truncate table {table_name}: {e}")

    objects_to_load = []
    try:
        csv_content = csv_file.read()
        try:
            csv_text = BytesIO(csv_content).read().decode('utf-8-sig')
        except UnicodeDecodeError:
            try:
                csv_text = BytesIO(csv_content).read().decode('latin-1')
            except UnicodeDecodeError:
                csv_text = BytesIO(csv_content).read().decode('cp1252')
        csv_reader = csv.reader(csv_text.splitlines())
        headers = ['role', 'user_name']
        next(csv_reader)
        field_map = {
            'ROLE': 0,
            'USER_NAME': 1
        }

        for i, row in enumerate(csv_reader):
            try:
                obj_data = {model_field: row[csv_index]
                            for model_field, csv_index in field_map.items()}
                auth_data_obj = DynamicUserRoleDataModel(**obj_data)
                objects_to_load.append(auth_data_obj)
            except IndexError as e:
                logger.error(f"Error processing row {i+2} in CSV data: Not enough columns. Row: {row}")
                print(f"Error processing row {i+2} in CSV data: Not enough columns. Row: {row}")
                raise DataLoaderError(f"Error processing row {i+2}: Not enough columns.")
            except Exception as row_e:
                print(f"Error processing row {i+2} in CSV data: {row_e}")
                print(f"Row data: {row}")
                logger.error(f"Error processing row {i+2} in CSV data: {row_e}")
                raise DataLoaderError(f"Error processing row {i+2}: {row_e}")

        if not objects_to_load:
            logger.warning(f"Warning: No data rows found in CSV data.")
            print(f"Warning: No data rows found in CSV data.")

        db.add_all(objects_to_load)
        db.commit()
        msg = f"Successfully loaded {len(objects_to_load)} records into {table_name}"
        logger.info(msg)
        print(msg)
        return {"message": msg, "table_name": table_name, "records_loaded": len(objects_to_load)}

    except Exception as e:
        db.rollback()
        logger.warning(f"Failed loading CSV data: {e}")
        raise DataLoaderError(f"Failed loading CSV data: {e}")


async def load_user_data_from_csv_upload(db: Session, csv_file, client_name: str, system_name: str):
    """Parses Role Auth CSV from a file-like object, ensures table exists, truncates, and loads data."""
    if not csv_file:
        logger.info(f"Skipping CSV data load for client: {client_name}, system: {system_name} as no file was provided.")
        print(f"Skipping CSV data load for client: {client_name}, system: {system_name} as no file was provided.")
        return {"message": "No CSV file provided, skipping load.", "table_name": None, "records_loaded": 0}

    logger.info(f"Starting CSV data load for client: {client_name}, system: {system_name}")

    DynamicUserDataModel = create_user_data(client_name, system_name) # Pass system_name
    table_name = DynamicUserDataModel.__tablename__
    engine = db.bind
    ensure_table_exists(engine, DynamicUserDataModel)

    try:
        deleted_count = db.query(DynamicUserDataModel).delete()
        logger.info(f"Truncated (deleted) {deleted_count} rows from {table_name}.")
        print(f"Truncated (deleted) {deleted_count} rows from {table_name}.")
    except Exception as e:
        db.rollback()
        logger.error(f"Failed to truncate table {table_name}: {e}", exc_info=True)
        raise DataLoaderError(f"Failed to truncate table {table_name}: {e}")

    objects_to_load = []
    try:
        csv_content = csv_file.read()
        try:
            csv_text = BytesIO(csv_content).read().decode('utf-8-sig')
        except UnicodeDecodeError:
            try:
                csv_text = BytesIO(csv_content).read().decode('latin-1')
            except UnicodeDecodeError:
                csv_text = BytesIO(csv_content).read().decode('cp1252')
        csv_reader = csv.reader(csv_text.splitlines())
        headers = ['user', 'full_name','id',
                   'current_classification','target_classification','ratio','ref_user','user_group','last_logon','count']
        next(csv_reader)
        field_map = {
            'USER': 0,
            'FULL_NAME': 1,
            'ID':2,
            'CURRENT_CLASSIFICATION':3,
            'TARGET_CLASSIFICATION':4,
            'RATIO':5,
            'REF_USER':6,
            'USER_GROUP':7,
            'LAST_LOGON':8,
            'COUNT':9
        }

        for i, row in enumerate(csv_reader):
            try:
                obj_data = {model_field: row[csv_index]
                            for model_field, csv_index in field_map.items()}
                auth_data_obj = DynamicUserDataModel(**obj_data)
                objects_to_load.append(auth_data_obj)
            except IndexError as e:
                logger.error(f"Error processing row {i+2} in CSV data: Not enough columns. Row: {row}")
                print(f"Error processing row {i+2} in CSV data: Not enough columns. Row: {row}")
                raise DataLoaderError(f"Error processing row {i+2}: Not enough columns.")
            except Exception as row_e:
                print(f"Error processing row {i+2} in CSV data: {row_e}")
                print(f"Row data: {row}")
                logger.error(f"Error processing row {i+2} in CSV data: {row_e}")
                raise DataLoaderError(f"Error processing row {i+2}: {row_e}")

        if not objects_to_load:
            logger.warning(f"Warning: No data rows found in CSV data.")
            print(f"Warning: No data rows found in CSV data.")

        db.add_all(objects_to_load)
        db.commit()
        msg = f"Successfully loaded {len(objects_to_load)} records into {table_name}"
        logger.info(msg)
        print(msg)
        return {"message": msg, "table_name": table_name, "records_loaded": len(objects_to_load)}

    except Exception as e:
        db.rollback()
        logger.warning(f"Failed loading CSV data: {e}")
        raise DataLoaderError(f"Failed loading CSV data: {e}")