import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Any, Optional
import json
import logging
from config.settings import settings

logger = logging.getLogger(__name__)

class SemanticLayer:
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=settings.chroma_persist_directory,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        self.embedding_model = SentenceTransformer(settings.embedding_model)
        self.collections = {}
        
    def create_schema_embeddings(self, schema_info: Dict[str, Any], connection_name: str = "default"):
        """Create embeddings for database schema information"""
        try:
            collection_name = f"schema_{connection_name}"
            
            # Delete existing collection if it exists
            try:
                self.client.delete_collection(collection_name)
            except:
                pass
            
            collection = self.client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            
            documents = []
            metadatas = []
            ids = []
            
            for table_name, table_info in schema_info.items():
                # Create document for table
                table_doc = f"Table: {table_name}\n"
                table_doc += f"Columns: {', '.join([col['name'] for col in table_info['columns']])}\n"
                
                # Add column details
                for col in table_info['columns']:
                    col_doc = f"Column {col['name']} in table {table_name}: type {col['type']}"
                    if not col['nullable']:
                        col_doc += " (NOT NULL)"
                    if col.get('primary_key'):
                        col_doc += " (PRIMARY KEY)"
                    
                    documents.append(col_doc)
                    metadatas.append({
                        'type': 'column',
                        'table': table_name,
                        'column': col['name'],
                        'data_type': str(col['type']),
                        'nullable': col['nullable']
                    })
                    ids.append(f"{table_name}_{col['name']}")
                
                # Add table-level document
                documents.append(table_doc)
                metadatas.append({
                    'type': 'table',
                    'table': table_name,
                    'column_count': len(table_info['columns'])
                })
                ids.append(f"table_{table_name}")
                
                # Add foreign key relationships
                for fk in table_info.get('foreign_keys', []):
                    fk_doc = f"Foreign key relationship: {table_name}.{fk['constrained_columns'][0]} references {fk['referred_table']}.{fk['referred_columns'][0]}"
                    documents.append(fk_doc)
                    metadatas.append({
                        'type': 'foreign_key',
                        'source_table': table_name,
                        'target_table': fk['referred_table'],
                        'source_column': fk['constrained_columns'][0],
                        'target_column': fk['referred_columns'][0]
                    })
                    ids.append(f"fk_{table_name}_{fk['constrained_columns'][0]}")
            
            # Add documents to collection in batches
            batch_size = 100
            for i in range(0, len(documents), batch_size):
                batch_docs = documents[i:i+batch_size]
                batch_metas = metadatas[i:i+batch_size]
                batch_ids = ids[i:i+batch_size]
                
                collection.add(
                    documents=batch_docs,
                    metadatas=batch_metas,
                    ids=batch_ids
                )
            
            self.collections[connection_name] = collection
            logger.info(f"Created schema embeddings for {len(documents)} items")
            
        except Exception as e:
            logger.error(f"Failed to create schema embeddings: {str(e)}")
            raise
    
    def search_relevant_schema(self, query: str, connection_name: str = "default", top_k: int = 10) -> List[Dict]:
        """Search for relevant schema elements based on natural language query"""
        try:
            collection_name = f"schema_{connection_name}"
            
            if connection_name not in self.collections:
                self.collections[connection_name] = self.client.get_collection(collection_name)
            
            results = self.collections[connection_name].query(
                query_texts=[query],
                n_results=top_k,
                include=['documents', 'metadatas', 'distances']
            )
            
            relevant_items = []
            for i, (doc, metadata, distance) in enumerate(zip(
                results['documents'][0],
                results['metadatas'][0], 
                results['distances'][0]
            )):
                relevant_items.append({
                    'document': doc,
                    'metadata': metadata,
                    'similarity_score': 1 - distance,  # Convert distance to similarity
                    'rank': i + 1
                })
            
            return relevant_items
            
        except Exception as e:
            logger.error(f"Schema search failed: {str(e)}")
            return []
    
    def get_relevant_tables_and_columns(self, query: str, connection_name: str = "default") -> Dict[str, List[str]]:
        """Get relevant tables and columns for a query"""
        relevant_items = self.search_relevant_schema(query, connection_name, top_k=20)
        
        tables_columns = {}
        
        for item in relevant_items:
            metadata = item['metadata']
            if metadata['type'] in ['column', 'table']:
                table_name = metadata['table']
                if table_name not in tables_columns:
                    tables_columns[table_name] = []
                
                if metadata['type'] == 'column':
                    column_name = metadata['column']
                    if column_name not in tables_columns[table_name]:
                        tables_columns[table_name].append(column_name)
        
        return tables_columns
    
    def create_business_glossary(self, glossary_terms: Dict[str, str], connection_name: str = "default"):
        """Create embeddings for business glossary terms"""
        try:
            collection_name = f"glossary_{connection_name}"
            
            # Delete existing collection if it exists
            try:
                self.client.delete_collection(collection_name)
            except:
                pass
            
            collection = self.client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            
            documents = []
            metadatas = []
            ids = []
            
            for term, definition in glossary_terms.items():
                doc = f"{term}: {definition}"
                documents.append(doc)
                metadatas.append({
                    'type': 'business_term',
                    'term': term,
                    'definition': definition
                })
                ids.append(f"term_{term}")
            
            collection.add(
                documents=documents,
                metadatas=metadatas,
                ids=ids
            )
            
            logger.info(f"Created business glossary with {len(documents)} terms")
            
        except Exception as e:
            logger.error(f"Failed to create business glossary: {str(e)}")
            raise

# Global instance
semantic_layer = SemanticLayer()
