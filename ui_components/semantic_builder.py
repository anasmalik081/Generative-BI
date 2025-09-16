import streamlit as st
import pandas as pd
from typing import Dict, Any, List
import json
import logging
from semantic_layer.enhanced_semantic_layer import enhanced_semantic_layer
from database.connection_manager import db_manager
from database.nosql_connection_manager import nosql_manager

logger = logging.getLogger(__name__)

class SemanticBuilderUI:
    def __init__(self):
        self.enhanced_metadata = {}
        self.sample_queries = []
    
    def render_semantic_builder(self, schema_info: Dict[str, Any], connection_name: str = "default"):
        """Render the semantic layer builder interface"""
        st.header("🧠 Enhanced Semantic Layer Builder")
        
        # Choose building method
        build_method = st.radio(
            "Choose how to build your semantic layer:",
            ["🤖 Automatic (AI-Generated)", "✏️ Manual (User-Defined)", "🔄 Hybrid (AI + Manual Editing)"],
            help="Automatic: AI generates all metadata. Manual: You provide all metadata. Hybrid: AI generates, you edit."
        )
        
        if build_method == "🤖 Automatic (AI-Generated)":
            self._render_automatic_builder(schema_info, connection_name)
        elif build_method == "✏️ Manual (User-Defined)":
            self._render_manual_builder(schema_info, connection_name)
        else:  # Hybrid
            self._render_hybrid_builder(schema_info, connection_name)
    
    def _render_automatic_builder(self, schema_info: Dict[str, Any], connection_name: str):
        """Render automatic semantic builder"""
        st.subheader("🤖 Automatic Semantic Layer Generation")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.info("AI will analyze your database schema and generate business-friendly metadata automatically.")
            
            # Options for automatic generation
            with st.expander("⚙️ Generation Options"):
                include_sample_data = st.checkbox(
                    "Analyze sample data for better context", 
                    value=True,
                    help="AI will look at actual data to understand column content better"
                )
                
                generate_examples = st.checkbox(
                    "Generate example values",
                    value=True,
                    help="AI will suggest realistic example values for each column"
                )
                
                business_domain = st.selectbox(
                    "Primary business domain (helps AI understand context):",
                    ["General", "E-commerce", "Finance", "Healthcare", "Manufacturing", "Education", "Real Estate", "Other"]
                )
        
        with col2:
            st.metric("Tables to Process", len(schema_info))
            total_columns = sum(len(table['columns']) for table in schema_info.values())
            st.metric("Total Columns", total_columns)
            
            estimated_time = max(1, total_columns // 50)  # Rough estimate
            st.metric("Estimated Time", f"{estimated_time} min")
        
        if st.button("🚀 Generate Semantic Layer", type="primary", use_container_width=True):
            self._execute_automatic_generation(schema_info, connection_name, {
                'include_sample_data': include_sample_data,
                'generate_examples': generate_examples,
                'business_domain': business_domain
            })
    
    def _render_manual_builder(self, schema_info: Dict[str, Any], connection_name: str):
        """Render manual semantic builder"""
        st.subheader("✏️ Manual Semantic Layer Definition")
        
        # Step 1: Download template
        st.write("**Step 1: Download Template**")
        template_df = enhanced_semantic_layer.export_enhanced_metadata_template(schema_info)
        
        col1, col2 = st.columns(2)
        with col1:
            csv_template = template_df.to_csv(index=False)
            st.download_button(
                label="📥 Download Metadata Template",
                data=csv_template,
                file_name="semantic_metadata_template.csv",
                mime="text/csv",
                help="Download this template, fill it out, and upload it back"
            )
        
        with col2:
            st.info(f"Template contains {len(template_df)} rows for all your columns")
        
        # Show template preview
        with st.expander("👀 Template Preview"):
            st.dataframe(template_df.head(10), use_container_width=True)
            st.caption("Fill out the alias_name, description, domain, examples, synonyms, and business_rules columns")
        
        # Step 2: Upload filled template
        st.write("**Step 2: Upload Completed Template**")
        uploaded_file = st.file_uploader(
            "Upload your completed metadata file",
            type=['csv'],
            help="Upload the CSV file with your business metadata"
        )
        
        if uploaded_file is not None:
            try:
                uploaded_df = pd.read_csv(uploaded_file)
                
                # Validate uploaded file
                required_columns = ['table_name', 'real_col_name', 'alias_name', 'type', 'description']
                missing_columns = [col for col in required_columns if col not in uploaded_df.columns]
                
                if missing_columns:
                    st.error(f"Missing required columns: {', '.join(missing_columns)}")
                else:
                    st.success(f"✅ Valid metadata file uploaded with {len(uploaded_df)} rows")
                    
                    # Preview uploaded data
                    with st.expander("📊 Uploaded Data Preview"):
                        st.dataframe(uploaded_df.head(10), use_container_width=True)
                    
                    # Step 3: Add sample queries
                    self._render_sample_queries_section()
                    
                    # Step 4: Build semantic layer
                    if st.button("🏗️ Build Semantic Layer", type="primary", use_container_width=True):
                        self._execute_manual_build(uploaded_df, connection_name)
                        
            except Exception as e:
                st.error(f"Error reading uploaded file: {str(e)}")
    
    def _render_hybrid_builder(self, schema_info: Dict[str, Any], connection_name: str):
        """Render hybrid semantic builder"""
        st.subheader("🔄 Hybrid Semantic Layer Builder")
        
        # Step 1: Generate automatically
        if 'generated_metadata' not in st.session_state:
            st.write("**Step 1: Generate Initial Metadata**")
            if st.button("🤖 Generate AI Metadata", type="primary"):
                with st.spinner("Generating AI metadata..."):
                    generated_metadata = enhanced_semantic_layer.generate_automatic_enhanced_metadata(schema_info)
                    st.session_state.generated_metadata = generated_metadata
                    st.success("✅ AI metadata generated successfully!")
                    st.rerun()
        
        # Step 2: Edit generated metadata
        if 'generated_metadata' in st.session_state:
            st.write("**Step 2: Review and Edit AI-Generated Metadata**")
            
            # Convert to editable DataFrame
            edit_df = self._convert_metadata_to_dataframe(st.session_state.generated_metadata, schema_info)
            
            # Allow editing
            edited_df = st.data_editor(
                edit_df,
                use_container_width=True,
                num_rows="dynamic",
                column_config={
                    "alias_name": st.column_config.TextColumn("Business Name", help="User-friendly column name"),
                    "description": st.column_config.TextColumn("Description", help="What this column represents"),
                    "domain": st.column_config.SelectboxColumn("Domain", options=["general", "sales", "customer", "product", "finance", "marketing", "operations"]),
                    "examples": st.column_config.TextColumn("Examples", help="Comma-separated example values"),
                }
            )
            
            # Step 3: Add sample queries
            self._render_sample_queries_section()
            
            # Step 4: Build semantic layer
            if st.button("🏗️ Build Enhanced Semantic Layer", type="primary", use_container_width=True):
                self._execute_hybrid_build(edited_df, connection_name)
    
    def _render_sample_queries_section(self):
        """Render section for adding sample queries"""
        st.write("**Sample Query-SQL Pairs (Optional but Recommended)**")
        
        with st.expander("➕ Add Sample Queries", expanded=False):
            st.info("Adding sample queries helps the AI understand your specific use cases and generates better SQL")
            
            # Initialize sample queries in session state
            if 'sample_queries' not in st.session_state:
                st.session_state.sample_queries = []
            
            # Add new query form
            with st.form("add_sample_query"):
                col1, col2 = st.columns(2)
                with col1:
                    question = st.text_area("Natural Language Question", placeholder="e.g., Show me top 10 customers by revenue")
                with col2:
                    sql = st.text_area("Corresponding SQL Query", placeholder="e.g., SELECT customer_name, SUM(total_amount) FROM...")
                
                explanation = st.text_input("Explanation (Optional)", placeholder="Brief explanation of the query logic")
                
                if st.form_submit_button("Add Query Pair"):
                    if question and sql:
                        st.session_state.sample_queries.append({
                            'question': question,
                            'sql': sql,
                            'explanation': explanation
                        })
                        st.success("Query pair added!")
                        st.rerun()
            
            # Display existing queries
            if st.session_state.sample_queries:
                st.write(f"**Added Query Pairs ({len(st.session_state.sample_queries)}):**")
                for i, query in enumerate(st.session_state.sample_queries):
                    with st.container():
                        col1, col2 = st.columns([4, 1])
                        with col1:
                            st.write(f"**Q{i+1}:** {query['question']}")
                            st.code(query['sql'], language='sql')
                        with col2:
                            if st.button("🗑️", key=f"delete_query_{i}", help="Delete this query"):
                                st.session_state.sample_queries.pop(i)
                                st.rerun()
    
    def _execute_automatic_generation(self, schema_info: Dict[str, Any], connection_name: str, options: Dict):
        """Execute automatic metadata generation"""
        try:
            with st.spinner("🤖 AI is analyzing your database schema..."):
                # Generate enhanced metadata
                enhanced_metadata = enhanced_semantic_layer.generate_automatic_enhanced_metadata(schema_info)
                
                # Get sample queries if any
                sample_queries = st.session_state.get('sample_queries', [])
                
                # Create enhanced embeddings
                enhanced_semantic_layer.create_enhanced_schema_embeddings(
                    schema_info=schema_info,
                    enhanced_metadata=enhanced_metadata,
                    sample_queries=sample_queries,
                    connection_name=connection_name
                )
                
                st.success("✅ Automatic semantic layer created successfully!")
                
                # Show summary
                self._show_semantic_layer_summary(enhanced_metadata, sample_queries)
                
                # Update session state
                st.session_state.semantic_layer_built = True
                st.session_state.semantic_method = "automatic"
                
        except Exception as e:
            st.error(f"❌ Failed to generate automatic semantic layer: {str(e)}")
            logger.error(f"Automatic generation failed: {str(e)}")
    
    def _execute_manual_build(self, metadata_df: pd.DataFrame, connection_name: str):
        """Execute manual semantic layer build"""
        try:
            with st.spinner("🏗️ Building semantic layer from your metadata..."):
                # Convert DataFrame to enhanced metadata format
                enhanced_metadata = enhanced_semantic_layer.import_enhanced_metadata_from_dataframe(metadata_df)
                
                # Get sample queries if any
                sample_queries = st.session_state.get('sample_queries', [])
                
                # Get schema info
                schema_info = db_manager.get_table_schema(connection_name)
                
                # Create enhanced embeddings
                enhanced_semantic_layer.create_enhanced_schema_embeddings(
                    schema_info=schema_info,
                    enhanced_metadata=enhanced_metadata,
                    sample_queries=sample_queries,
                    connection_name=connection_name
                )
                
                st.success("✅ Manual semantic layer created successfully!")
                
                # Show summary
                self._show_semantic_layer_summary(enhanced_metadata, sample_queries)
                
                # Update session state
                st.session_state.semantic_layer_built = True
                st.session_state.semantic_method = "manual"
                
        except Exception as e:
            st.error(f"❌ Failed to build manual semantic layer: {str(e)}")
            logger.error(f"Manual build failed: {str(e)}")
    
    def _execute_hybrid_build(self, edited_df: pd.DataFrame, connection_name: str):
        """Execute hybrid semantic layer build"""
        try:
            with st.spinner("🔄 Building hybrid semantic layer..."):
                # Convert DataFrame to enhanced metadata format
                enhanced_metadata = enhanced_semantic_layer.import_enhanced_metadata_from_dataframe(edited_df)
                
                # Get sample queries if any
                sample_queries = st.session_state.get('sample_queries', [])
                
                # Get schema info
                schema_info = db_manager.get_table_schema(connection_name)
                
                # Create enhanced embeddings
                enhanced_semantic_layer.create_enhanced_schema_embeddings(
                    schema_info=schema_info,
                    enhanced_metadata=enhanced_metadata,
                    sample_queries=sample_queries,
                    connection_name=connection_name
                )
                
                st.success("✅ Hybrid semantic layer created successfully!")
                
                # Show summary
                self._show_semantic_layer_summary(enhanced_metadata, sample_queries)
                
                # Update session state
                st.session_state.semantic_layer_built = True
                st.session_state.semantic_method = "hybrid"
                
        except Exception as e:
            st.error(f"❌ Failed to build hybrid semantic layer: {str(e)}")
            logger.error(f"Hybrid build failed: {str(e)}")
    
    def _convert_metadata_to_dataframe(self, metadata: Dict[str, Any], schema_info: Dict[str, Any]) -> pd.DataFrame:
        """Convert metadata dictionary to editable DataFrame"""
        rows = []
        
        for table_name, table_meta in metadata.items():
            if table_name in schema_info:
                for col in schema_info[table_name]['columns']:
                    col_name = col['name']
                    col_meta = table_meta.get('columns', {}).get(col_name, {})
                    
                    rows.append({
                        'table_name': table_name,
                        'real_col_name': col_name,
                        'alias_name': col_meta.get('alias_name', col_name),
                        'type': str(col['type']),
                        'description': col_meta.get('description', ''),
                        'domain': col_meta.get('domain', 'general'),
                        'examples': ', '.join(col_meta.get('examples', [])),
                        'synonyms': ', '.join(col_meta.get('synonyms', [])),
                        'business_rules': col_meta.get('business_rules', '')
                    })
        
        return pd.DataFrame(rows)
    
    def _show_semantic_layer_summary(self, enhanced_metadata: Dict[str, Any], sample_queries: List[Dict]):
        """Show summary of created semantic layer"""
        st.subheader("📊 Semantic Layer Summary")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            table_count = len(enhanced_metadata)
            st.metric("Enhanced Tables", table_count)
        
        with col2:
            column_count = sum(len(table.get('columns', {})) for table in enhanced_metadata.values())
            st.metric("Enhanced Columns", column_count)
        
        with col3:
            alias_count = sum(
                1 for table in enhanced_metadata.values()
                for col_meta in table.get('columns', {}).values()
                if col_meta.get('alias_name') and col_meta['alias_name'] != col_meta.get('real_col_name', '')
            )
            st.metric("Business Aliases", alias_count)
        
        with col4:
            st.metric("Sample Queries", len(sample_queries))
        
        # Show some examples
        with st.expander("🔍 Enhanced Metadata Examples"):
            for table_name, table_meta in list(enhanced_metadata.items())[:2]:  # Show first 2 tables
                st.write(f"**Table: {table_name}**")
                if table_meta.get('description'):
                    st.write(f"*Description: {table_meta['description']}*")
                
                # Show first few enhanced columns
                for col_name, col_meta in list(table_meta.get('columns', {}).items())[:3]:
                    if col_meta.get('alias_name') != col_name:
                        st.write(f"• {col_name} → **{col_meta['alias_name']}**: {col_meta.get('description', 'No description')}")

# Global instance
semantic_builder_ui = SemanticBuilderUI()
