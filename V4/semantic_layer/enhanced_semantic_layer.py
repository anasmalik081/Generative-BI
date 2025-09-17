import chromadb
from chromadb.config import Settings as ChromaSettings
from typing import List, Dict, Any, Optional, Tuple
import json
import pandas as pd
import logging
from config.settings import settings
from config.llm_factory import llm_factory
from langchain.prompts import ChatPromptTemplate
import uuid

logger = logging.getLogger(__name__)

class EnhancedSemanticLayer:
    def __init__(self):
        self.client = chromadb.PersistentClient(
            path=settings.chroma_persist_directory,
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        self.embedding_model = llm_factory.get_embedding_model()
        self.llm = llm_factory.get_chat_model()
        self.collections = {}
    
    def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings using configured model"""
        if settings.ai_provider == "openai":
            return self.embedding_model.embed_documents(texts)
        else:
            return self.embedding_model.encode(texts).tolist()
        
    def _safe_metadata_value(self, value):
        """Convert metadata value to ChromaDB-compatible format"""
        if value is None:
            return ""
        elif isinstance(value, (str, int, float, bool)):
            return value
        elif isinstance(value, list):
            return ', '.join(map(str, value)) if value else ""
        elif isinstance(value, dict):
            return str(value)
        else:
            return str(value)
    
    def refresh_embedding_function(self):
        """Refresh embedding function when provider changes"""
        from config.chroma_embedding_function import CustomEmbeddingFunction
        self.embedding_function = CustomEmbeddingFunction()
        self.collections = {}  # Clear cache to force reload with new embedding function
        logger.info("Embedding function refreshed for new AI provider")
    
    def check_existing_embeddings(self, connection_name: str = "default") -> bool:
        """Check if embeddings already exist for this connection"""
        try:
            collection_name = f"enhanced_schema_{connection_name}"
            collection = self.client.get_collection(collection_name)
            count = collection.count()
            logger.info(f"Found existing collection '{collection_name}' with {count} embeddings")
            return count > 0
        except Exception as e:
            logger.info(f"No existing embeddings found for '{connection_name}': {e}")
            return False
    
    def get_existing_collection_info(self, connection_name: str = "default") -> Dict[str, Any]:
        """Get information about existing collection"""
        try:
            collection_name = f"enhanced_schema_{connection_name}"
            collection = self.client.get_collection(collection_name)
            count = collection.count()
            
            # Get sample metadata to understand what's stored
            sample_results = collection.peek(limit=5)
            tables = set()
            for metadata in sample_results.get('metadatas', []):
                if metadata and 'table' in metadata:
                    tables.add(metadata['table'])
            
            return {
                "exists": True,
                "count": count,
                "tables": list(tables),
                "collection_name": collection_name
            }
        except Exception as e:
            return {"exists": False, "error": str(e)}
    
    def create_enhanced_schema_embeddings(self, 
                                        schema_info: Dict[str, Any], 
                                        enhanced_metadata: Dict[str, Any] = None,
                                        sample_queries: List[Dict[str, str]] = None,
                                        connection_name: str = "default",
                                        force_rebuild: bool = False):
        """Create enhanced embeddings with business context"""
        try:
            collection_name = f"enhanced_schema_{connection_name}"
            
            # Check if embeddings already exist and force_rebuild is False
            if not force_rebuild and self.check_existing_embeddings(connection_name):
                logger.info(f"Using existing embeddings for '{connection_name}'")
                return True
            
            # Delete existing collection if it exists (only when rebuilding)
            try:
                self.client.delete_collection(collection_name)
                logger.info(f"Deleted existing collection '{collection_name}' for rebuild")
            except:
                pass
            
            collection = self.client.create_collection(
                name=collection_name,
                metadata={"hnsw:space": "cosine"}
            )
            
            documents = []
            metadatas = []
            ids = []
            
            # Process each table
            for table_name, table_info in schema_info.items():
                # Get enhanced metadata for this table if available
                table_enhanced = enhanced_metadata.get(table_name, {}) if enhanced_metadata else {}
                
                # Create comprehensive table document
                table_doc = self._create_enhanced_table_document(
                    table_name, table_info, table_enhanced
                )
                
                documents.append(table_doc)
                metadatas.append({
                    'type': 'enhanced_table',
                    'table': table_name,
                    'column_count': len(table_info['columns']),
                    'business_description': self._safe_metadata_value(table_enhanced.get('description', '')),
                    'domain': self._safe_metadata_value(table_enhanced.get('domain', 'general')),
                    'common_use_cases': self._safe_metadata_value(table_enhanced.get('common_use_cases', []))
                })
                ids.append(f"enhanced_table_{table_name}")
                
                # Process columns with enhanced metadata
                for col in table_info['columns']:
                    col_enhanced = table_enhanced.get('columns', {}).get(col['name'], {})
                    
                    col_doc = self._create_enhanced_column_document(
                        table_name, col, col_enhanced
                    )
                    
                    documents.append(col_doc)
                    metadatas.append({
                        'type': 'enhanced_column',
                        'table': table_name,
                        'column': col['name'],
                        'data_type': str(col['type']),
                        'nullable': col['nullable'],
                        'alias_name': self._safe_metadata_value(col_enhanced.get('alias_name', col['name'])),
                        'business_description': self._safe_metadata_value(col_enhanced.get('description', '')),
                        'domain': self._safe_metadata_value(col_enhanced.get('domain', 'general')),
                        'examples': self._safe_metadata_value(col_enhanced.get('examples', []))
                    })
                    ids.append(f"enhanced_col_{table_name}_{col['name']}")
                
                # Add relationship documents
                for fk in table_info.get('foreign_keys', []):
                    rel_doc = self._create_relationship_document(table_name, fk)
                    documents.append(rel_doc)
                    metadatas.append({
                        'type': 'relationship',
                        'source_table': table_name,
                        'target_table': fk['referred_table'],
                        'relationship_type': 'foreign_key'
                    })
                    ids.append(f"rel_{table_name}_{fk['constrained_columns'][0]}")
            
            # Add sample queries if provided
            if sample_queries:
                for i, query_pair in enumerate(sample_queries):
                    query_doc = f"Question: {query_pair['question']}\nSQL: {query_pair['sql']}\nExplanation: {query_pair.get('explanation', '')}"
                    documents.append(query_doc)
                    metadatas.append({
                        'type': 'sample_query',
                        'question': self._safe_metadata_value(query_pair['question']),
                        'sql': self._safe_metadata_value(query_pair['sql']),
                        'tables_used': self._safe_metadata_value(query_pair.get('tables_used', []))
                    })
                    ids.append(f"sample_query_{i}")
            
            # Generate embeddings for all documents
            embeddings = self._generate_embeddings(documents)
            
            # Add documents in batches
            batch_size = 100
            for i in range(0, len(documents), batch_size):
                batch_docs = documents[i:i+batch_size]
                batch_metas = metadatas[i:i+batch_size]
                batch_ids = ids[i:i+batch_size]
                batch_embeddings = embeddings[i:i+batch_size]
                
                collection.add(
                    documents=batch_docs,
                    metadatas=batch_metas,
                    ids=batch_ids,
                    embeddings=batch_embeddings
                )
            
            self.collections[connection_name] = collection
            logger.info(f"Created enhanced schema embeddings for {len(documents)} items")
            
        except Exception as e:
            logger.error(f"Failed to create enhanced schema embeddings: {str(e)}")
            raise
    
    def _create_enhanced_table_document(self, table_name: str, table_info: Dict, enhanced_info: Dict) -> str:
        """Create comprehensive table document"""
        doc = f"Table: {table_name}\n"
        
        # Add business description if available
        if enhanced_info.get('description'):
            doc += f"Business Description: {enhanced_info['description']}\n"
        
        # Add domain/category
        if enhanced_info.get('domain'):
            doc += f"Domain: {enhanced_info['domain']}\n"
        
        # Add column summary
        columns = table_info['columns']
        doc += f"Total Columns: {len(columns)}\n"
        
        # Add key columns with business names
        key_columns = []
        for col in columns[:10]:  # First 10 columns
            col_enhanced = enhanced_info.get('columns', {}).get(col['name'], {})
            alias_name = col_enhanced.get('alias_name', col['name'])
            if alias_name != col['name']:
                key_columns.append(f"{col['name']} (Business Name: {alias_name})")
            else:
                key_columns.append(col['name'])
        
        doc += f"Key Columns: {', '.join(key_columns)}\n"
        
        # Add business context
        if enhanced_info.get('business_rules'):
            doc += f"Business Rules: {enhanced_info['business_rules']}\n"
        
        # Add usage examples
        if enhanced_info.get('common_use_cases'):
            doc += f"Common Use Cases: {', '.join(enhanced_info['common_use_cases'])}\n"
        
        return doc
    
    def _create_enhanced_column_document(self, table_name: str, col_info: Dict, enhanced_info: Dict) -> str:
        """Create comprehensive column document"""
        col_name = col_info['name']
        alias_name = enhanced_info.get('alias_name', col_name)
        
        doc = f"Column: {col_name} in table {table_name}\n"
        
        if alias_name != col_name:
            doc += f"Business Name: {alias_name}\n"
        
        doc += f"Data Type: {col_info['type']}\n"
        
        if enhanced_info.get('description'):
            doc += f"Description: {enhanced_info['description']}\n"
        
        if enhanced_info.get('domain'):
            doc += f"Domain: {enhanced_info['domain']}\n"
        
        # Add examples if available
        if enhanced_info.get('examples'):
            examples = enhanced_info['examples'][:3]  # First 3 examples
            doc += f"Example Values: {', '.join(map(str, examples))}\n"
        
        # Add business rules
        if enhanced_info.get('business_rules'):
            doc += f"Business Rules: {enhanced_info['business_rules']}\n"
        
        # Add related terms
        if enhanced_info.get('synonyms'):
            doc += f"Also Known As: {', '.join(enhanced_info['synonyms'])}\n"
        
        return doc
    
    def _create_relationship_document(self, table_name: str, fk_info: Dict) -> str:
        """Create relationship document"""
        source_col = fk_info['constrained_columns'][0] if fk_info['constrained_columns'] else 'unknown'
        target_table = fk_info['referred_table']
        target_col = fk_info['referred_columns'][0] if fk_info['referred_columns'] else 'unknown'
        
        doc = f"Relationship: {table_name}.{source_col} references {target_table}.{target_col}\n"
        doc += f"This creates a link between {table_name} and {target_table} tables\n"
        doc += f"Use this relationship to join data from both tables\n"
        
        return doc
    
    def generate_automatic_enhanced_metadata(self, schema_info: Dict[str, Any], progress_callback=None) -> Dict[str, Any]:
        """Automatically generate enhanced metadata using LLM with progress tracking"""
        try:
            enhanced_metadata = {}
            total_tables = len(schema_info)
            
            for i, (table_name, table_info) in enumerate(schema_info.items()):
                if progress_callback:
                    progress_callback(f"🔍 Analyzing table: {table_name}", i, total_tables)
                
                logger.info(f"Generating enhanced metadata for table: {table_name} ({i+1}/{total_tables})")
                
                # Generate table-level metadata
                if progress_callback:
                    progress_callback(f"📋 Generating table metadata for: {table_name}", i, total_tables)
                
                table_enhanced = self._generate_table_metadata(table_name, table_info)
                
                # Generate column-level metadata
                if progress_callback:
                    progress_callback(f"📊 Processing {len(table_info['columns'])} columns in: {table_name}", i, total_tables)
                
                columns_enhanced = {}
                total_columns = len(table_info['columns'])
                
                for j, col in enumerate(table_info['columns']):
                    if progress_callback and j % 5 == 0:  # Update every 5 columns to avoid too many updates
                        progress_callback(f"📊 Column {j+1}/{total_columns} in {table_name}: {col['name']}", i, total_tables)
                    
                    col_enhanced = self._generate_column_metadata(table_name, col, table_info)
                    columns_enhanced[col['name']] = col_enhanced
                
                enhanced_metadata[table_name] = {
                    **table_enhanced,
                    'columns': columns_enhanced
                }
                
                if progress_callback:
                    progress_callback(f"✅ Completed: {table_name}", i + 1, total_tables)
            
            if progress_callback:
                progress_callback("🎉 All tables processed successfully!", total_tables, total_tables)
            
            return enhanced_metadata
            
        except Exception as e:
            logger.error(f"Failed to generate automatic enhanced metadata: {str(e)}")
            if progress_callback:
                progress_callback(f"❌ Error: {str(e)}", 0, 1)
            return {}
    
    def _generate_table_metadata(self, table_name: str, table_info: Dict) -> Dict[str, Any]:
        """Generate table-level enhanced metadata"""
        try:
            columns_summary = []
            for col in table_info['columns'][:20]:  # First 20 columns
                columns_summary.append(f"{col['name']} ({col['type']})")
            
            prompt = ChatPromptTemplate.from_template("""
            Analyze this database table and provide business context:
            
            Table Name: {table_name}
            Columns: {columns}
            
            Please provide:
            1. A business description of what this table represents
            2. The business domain (e.g., sales, customer, product, finance, etc.)
            3. Common use cases for this table
            4. Any business rules that might apply
            
            Respond in JSON format:
            {{
                "description": "Business description",
                "domain": "business domain",
                "common_use_cases": ["use case 1", "use case 2"],
                "business_rules": "Any important business rules"
            }}
            """)
            
            response = self.llm.invoke(prompt.format_messages(
                table_name=table_name,
                columns=", ".join(columns_summary)
            ))
            
            # Parse JSON response
            try:
                import json
                metadata = json.loads(response.content)
                
                # Ensure all values are safe for ChromaDB
                safe_metadata = {}
                for key, value in metadata.items():
                    safe_metadata[key] = self._safe_metadata_value(value)
                
                return safe_metadata
                
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                return {
                    "description": f"Database table containing {table_name} related information",
                    "domain": "general",
                    "common_use_cases": "data analysis, reporting",
                    "business_rules": "Standard database constraints apply"
                }
                
        except Exception as e:
            logger.error(f"Failed to generate table metadata for {table_name}: {str(e)}")
            return {
                "description": f"Table: {table_name}",
                "domain": "general", 
                "common_use_cases": "data storage",
                "business_rules": ""
            }
    
    def _generate_column_metadata(self, table_name: str, col_info: Dict, table_info: Dict) -> Dict[str, Any]:
        """Generate column-level enhanced metadata"""
        try:
            col_name = col_info['name']
            col_type = str(col_info['type'])
            
            prompt = ChatPromptTemplate.from_template("""
            Analyze this database column and provide business context:
            
            Table: {table_name}
            Column: {col_name}
            Data Type: {col_type}
            Nullable: {nullable}
            
            Please provide:
            1. A business-friendly alias name (if the current name is unclear)
            2. A clear description of what this column represents
            3. The business domain/category
            4. Possible example values
            5. Any synonyms or alternative names
            
            Respond in JSON format:
            {{
                "alias_name": "Business friendly name",
                "description": "Clear description",
                "domain": "business domain",
                "examples": ["example1", "example2"],
                "synonyms": ["synonym1", "synonym2"],
                "business_rules": "Any validation rules"
            }}
            """)
            
            response = self.llm.invoke(prompt.format_messages(
                table_name=table_name,
                col_name=col_name,
                col_type=col_type,
                nullable=col_info.get('nullable', True)
            ))
            
            # Parse JSON response
            try:
                import json
                metadata = json.loads(response.content)
                
                # Ensure all values are safe for ChromaDB
                safe_metadata = {}
                for key, value in metadata.items():
                    safe_metadata[key] = self._safe_metadata_value(value)
                
                return safe_metadata
                
            except json.JSONDecodeError:
                # Fallback if JSON parsing fails
                return {
                    "alias_name": col_name.replace('_', ' ').title(),
                    "description": f"Column storing {col_name} information",
                    "domain": "general",
                    "examples": "",
                    "synonyms": "",
                    "business_rules": ""
                }
                
        except Exception as e:
            logger.error(f"Failed to generate column metadata for {col_name}: {str(e)}")
            return {
                "alias_name": col_info['name'].replace('_', ' ').title(),
                "description": f"Column: {col_info['name']}",
                "domain": "general",
                "examples": "",
                "synonyms": "",
                "business_rules": ""
            }
    
    def search_enhanced_schema(self, query: str, connection_name: str = "default", top_k: int = 15) -> List[Dict]:
        """Search enhanced schema with better context understanding"""
        try:
            collection_name = f"enhanced_schema_{connection_name}"
            
            if connection_name not in self.collections:
                self.collections[connection_name] = self.client.get_collection(collection_name)
            
            # Generate query embedding
            query_embedding = self._generate_embeddings([query])[0]
            
            # Search with multiple strategies
            results = self.collections[connection_name].query(
                query_embeddings=[query_embedding],
                n_results=top_k,
                include=['documents', 'metadatas', 'distances']
            )
            
            enhanced_items = []
            for i, (doc, metadata, distance) in enumerate(zip(
                results['documents'][0],
                results['metadatas'][0], 
                results['distances'][0]
            )):
                enhanced_items.append({
                    'document': doc,
                    'metadata': metadata,
                    'similarity_score': 1 - distance,
                    'rank': i + 1
                })
            
            # Re-rank based on business context
            enhanced_items = self._rerank_by_business_context(enhanced_items, query)
            
            return enhanced_items
            
        except Exception as e:
            logger.error(f"Enhanced schema search failed: {str(e)}")
            return []
    
    def _rerank_by_business_context(self, items: List[Dict], query: str) -> List[Dict]:
        """Re-rank results based on business context"""
        # Boost items with business descriptions
        for item in items:
            metadata = item['metadata']
            
            # Boost if has business description
            if metadata.get('business_description'):
                item['similarity_score'] *= 1.2
            
            # Boost if has alias name different from column name
            if metadata.get('type') == 'enhanced_column':
                if metadata.get('alias_name') != metadata.get('column'):
                    item['similarity_score'] *= 1.1
            
            # Boost sample queries
            if metadata.get('type') == 'sample_query':
                item['similarity_score'] *= 1.3
        
        # Sort by adjusted similarity score
        return sorted(items, key=lambda x: x['similarity_score'], reverse=True)
    
    def export_enhanced_metadata_template(self, schema_info: Dict[str, Any]) -> pd.DataFrame:
        """Export template for manual metadata entry"""
        rows = []
        
        for table_name, table_info in schema_info.items():
            for col in table_info['columns']:
                rows.append({
                    'table_name': table_name,
                    'real_col_name': col['name'],
                    'alias_name': col['name'].replace('_', ' ').title(),  # Default suggestion
                    'type': str(col['type']),
                    'description': '',  # To be filled by user
                    'domain': '',  # To be filled by user
                    'examples': '',  # To be filled by user
                    'synonyms': '',  # To be filled by user
                    'business_rules': ''  # To be filled by user
                })
        
        return pd.DataFrame(rows)
    
    def import_enhanced_metadata_from_dataframe(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Import enhanced metadata from user-filled DataFrame"""
        enhanced_metadata = {}
        
        for _, row in df.iterrows():
            table_name = row['table_name']
            
            if table_name not in enhanced_metadata:
                enhanced_metadata[table_name] = {'columns': {}}
            
            col_name = row['real_col_name']
            enhanced_metadata[table_name]['columns'][col_name] = {
                'alias_name': row.get('alias_name', col_name),
                'description': row.get('description', ''),
                'domain': row.get('domain', 'general'),
                'examples': row.get('examples', '').split(',') if row.get('examples') else [],
                'synonyms': row.get('synonyms', '').split(',') if row.get('synonyms') else [],
                'business_rules': row.get('business_rules', '')
            }
        
        return enhanced_metadata

# Global instance
enhanced_semantic_layer = EnhancedSemanticLayer()
