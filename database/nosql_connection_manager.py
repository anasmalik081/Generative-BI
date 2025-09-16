import boto3
import pandas as pd
from typing import Dict, List, Any, Optional
import logging
from config.settings import settings
from boto3.dynamodb.conditions import Key, Attr
import json

logger = logging.getLogger(__name__)

class NoSQLConnectionManager:
    def __init__(self):
        self.dynamodb_client = None
        self.dynamodb_resource = None
        self.athena_client = None
        self.s3_client = None
        self.connections = {}
    
    def connect_dynamodb(self, region_name: str = "us-east-1", **kwargs) -> bool:
        """Connect to DynamoDB"""
        try:
            session = boto3.Session(
                aws_access_key_id=kwargs.get('aws_access_key_id'),
                aws_secret_access_key=kwargs.get('aws_secret_access_key'),
                region_name=region_name
            )
            
            self.dynamodb_client = session.client('dynamodb')
            self.dynamodb_resource = session.resource('dynamodb')
            
            # Test connection
            self.dynamodb_client.list_tables()
            
            self.connections['dynamodb'] = {
                'client': self.dynamodb_client,
                'resource': self.dynamodb_resource,
                'type': 'dynamodb'
            }
            
            logger.info("Successfully connected to DynamoDB")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to DynamoDB: {str(e)}")
            return False
    
    def connect_athena(self, region_name: str = "us-east-1", s3_output_location: str = None, **kwargs) -> bool:
        """Connect to Athena"""
        try:
            session = boto3.Session(
                aws_access_key_id=kwargs.get('aws_access_key_id'),
                aws_secret_access_key=kwargs.get('aws_secret_access_key'),
                region_name=region_name
            )
            
            self.athena_client = session.client('athena')
            self.s3_client = session.client('s3')
            
            # Test connection
            self.athena_client.list_databases(CatalogName='AwsDataCatalog')
            
            self.connections['athena'] = {
                'client': self.athena_client,
                's3_client': self.s3_client,
                's3_output_location': s3_output_location or 's3://aws-athena-query-results-default/',
                'type': 'athena'
            }
            
            logger.info("Successfully connected to Athena")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to Athena: {str(e)}")
            return False
    
    def get_dynamodb_tables(self) -> List[str]:
        """Get list of DynamoDB tables"""
        try:
            if 'dynamodb' not in self.connections:
                return []
            
            response = self.dynamodb_client.list_tables()
            return response.get('TableNames', [])
            
        except Exception as e:
            logger.error(f"Failed to get DynamoDB tables: {str(e)}")
            return []
    
    def get_dynamodb_table_schema(self, table_name: str) -> Dict[str, Any]:
        """Get DynamoDB table schema"""
        try:
            if 'dynamodb' not in self.connections:
                return {}
            
            response = self.dynamodb_client.describe_table(TableName=table_name)
            table_info = response['Table']
            
            # Extract key schema and attributes
            key_schema = table_info.get('KeySchema', [])
            attributes = {attr['AttributeName']: attr['AttributeType'] 
                         for attr in table_info.get('AttributeDefinitions', [])}
            
            # Sample some items to understand structure
            table = self.dynamodb_resource.Table(table_name)
            sample_response = table.scan(Limit=5)
            sample_items = sample_response.get('Items', [])
            
            # Infer additional attributes from sample data
            all_attributes = set(attributes.keys())
            for item in sample_items:
                all_attributes.update(item.keys())
            
            schema_info = {
                'table_name': table_name,
                'key_schema': key_schema,
                'attributes': attributes,
                'all_attributes': list(all_attributes),
                'sample_items': sample_items[:3],  # Keep only 3 samples
                'item_count': table_info.get('ItemCount', 0)
            }
            
            return schema_info
            
        except Exception as e:
            logger.error(f"Failed to get DynamoDB table schema for {table_name}: {str(e)}")
            return {}
    
    def query_dynamodb(self, table_name: str, key_condition: str = None, 
                      filter_expression: str = None, limit: int = 100) -> pd.DataFrame:
        """Query DynamoDB table"""
        try:
            if 'dynamodb' not in self.connections:
                return pd.DataFrame()
            
            table = self.dynamodb_resource.Table(table_name)
            
            if key_condition:
                # This is a simplified approach - in practice, you'd need to parse the condition
                response = table.query(Limit=limit)
            else:
                response = table.scan(Limit=limit)
            
            items = response.get('Items', [])
            
            # Convert DynamoDB items to DataFrame
            if items:
                df = pd.json_normalize(items)
                return df
            else:
                return pd.DataFrame()
                
        except Exception as e:
            logger.error(f"Failed to query DynamoDB table {table_name}: {str(e)}")
            return pd.DataFrame()
    
    def get_athena_databases(self) -> List[str]:
        """Get list of Athena databases"""
        try:
            if 'athena' not in self.connections:
                return []
            
            response = self.athena_client.list_databases(CatalogName='AwsDataCatalog')
            return [db['Name'] for db in response.get('DatabaseList', [])]
            
        except Exception as e:
            logger.error(f"Failed to get Athena databases: {str(e)}")
            return []
    
    def get_athena_tables(self, database_name: str) -> List[str]:
        """Get list of tables in Athena database"""
        try:
            if 'athena' not in self.connections:
                return []
            
            response = self.athena_client.list_table_metadata(
                CatalogName='AwsDataCatalog',
                DatabaseName=database_name
            )
            return [table['Name'] for table in response.get('TableMetadataList', [])]
            
        except Exception as e:
            logger.error(f"Failed to get Athena tables for {database_name}: {str(e)}")
            return []
    
    def get_athena_table_schema(self, database_name: str, table_name: str) -> Dict[str, Any]:
        """Get Athena table schema"""
        try:
            if 'athena' not in self.connections:
                return {}
            
            response = self.athena_client.get_table_metadata(
                CatalogName='AwsDataCatalog',
                DatabaseName=database_name,
                TableName=table_name
            )
            
            table_metadata = response['TableMetadata']
            columns = []
            
            for col in table_metadata.get('Columns', []):
                columns.append({
                    'name': col['Name'],
                    'type': col['Type'],
                    'comment': col.get('Comment', ''),
                    'nullable': True  # Athena doesn't have NOT NULL constraints
                })
            
            return {
                'table_name': table_name,
                'database_name': database_name,
                'columns': columns,
                'location': table_metadata.get('Parameters', {}).get('location', ''),
                'input_format': table_metadata.get('Parameters', {}).get('inputformat', ''),
                'output_format': table_metadata.get('Parameters', {}).get('outputformat', '')
            }
            
        except Exception as e:
            logger.error(f"Failed to get Athena table schema for {database_name}.{table_name}: {str(e)}")
            return {}
    
    def execute_athena_query(self, query: str, database_name: str = 'default') -> pd.DataFrame:
        """Execute Athena query"""
        try:
            if 'athena' not in self.connections:
                return pd.DataFrame()
            
            athena_conn = self.connections['athena']
            
            # Start query execution
            response = athena_conn['client'].start_query_execution(
                QueryString=query,
                QueryExecutionContext={'Database': database_name},
                ResultConfiguration={
                    'OutputLocation': athena_conn['s3_output_location']
                }
            )
            
            query_execution_id = response['QueryExecutionId']
            
            # Wait for query to complete
            import time
            max_wait_time = 300  # 5 minutes
            wait_time = 0
            
            while wait_time < max_wait_time:
                response = athena_conn['client'].get_query_execution(
                    QueryExecutionId=query_execution_id
                )
                
                status = response['QueryExecution']['Status']['State']
                
                if status in ['SUCCEEDED']:
                    break
                elif status in ['FAILED', 'CANCELLED']:
                    error_msg = response['QueryExecution']['Status'].get('StateChangeReason', 'Unknown error')
                    raise Exception(f"Query failed: {error_msg}")
                
                time.sleep(2)
                wait_time += 2
            
            if wait_time >= max_wait_time:
                raise Exception("Query timeout")
            
            # Get query results
            result_response = athena_conn['client'].get_query_results(
                QueryExecutionId=query_execution_id
            )
            
            # Convert to DataFrame
            rows = result_response['ResultSet']['Rows']
            if not rows:
                return pd.DataFrame()
            
            # Extract column names from first row
            columns = [col['VarCharValue'] for col in rows[0]['Data']]
            
            # Extract data rows
            data = []
            for row in rows[1:]:  # Skip header row
                data.append([col.get('VarCharValue', '') for col in row['Data']])
            
            df = pd.DataFrame(data, columns=columns)
            logger.info(f"Athena query executed successfully, returned {len(df)} rows")
            return df
            
        except Exception as e:
            logger.error(f"Failed to execute Athena query: {str(e)}")
            return pd.DataFrame()

# Global instance
nosql_manager = NoSQLConnectionManager()
