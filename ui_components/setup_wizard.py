import streamlit as st
import pandas as pd
from typing import Dict, Any, List
import logging
import time
from datetime import datetime
from config.settings import settings
from database.connection_manager import db_manager
from database.nosql_connection_manager import nosql_manager
from semantic_layer.enhanced_semantic_layer import enhanced_semantic_layer

logger = logging.getLogger(__name__)

class SetupWizard:
    def __init__(self):
        self.steps = [
            "Database Connection",
            "Schema Analysis", 
            "Semantic Layer Setup",
            "Ready to Query"
        ]
    
    def render_wizard(self):
        """Render the complete setup wizard"""
        # Initialize wizard state
        if 'wizard_step' not in st.session_state:
            st.session_state.wizard_step = 0
        if 'wizard_completed' not in st.session_state:
            st.session_state.wizard_completed = False
        
        # Show progress
        self._show_progress()
        
        # Render current step
        if st.session_state.wizard_step == 0:
            self._step_database_connection()
        elif st.session_state.wizard_step == 1:
            self._step_schema_analysis()
        elif st.session_state.wizard_step == 2:
            self._step_semantic_setup()
        elif st.session_state.wizard_step == 3:
            self._step_ready_to_query()
    
    def _show_progress(self):
        """Show wizard progress"""
        st.markdown("### 🚀 GenBI Setup Wizard")
        
        # Progress bar
        progress = (st.session_state.wizard_step + 1) / len(self.steps)
        st.progress(progress)
        
        # Step indicators
        cols = st.columns(len(self.steps))
        for i, (col, step_name) in enumerate(zip(cols, self.steps)):
            with col:
                if i < st.session_state.wizard_step:
                    st.success(f"✅ {step_name}")
                elif i == st.session_state.wizard_step:
                    st.info(f"🔄 {step_name}")
                else:
                    st.write(f"⏳ {step_name}")
        
        st.markdown("---")
    
    def _step_database_connection(self):
        """Step 1: Database Connection"""
        st.header("🔗 Step 1: Connect to Your Database")
        st.write("Choose your database type and provide connection details.")
        
        # Database type selection (without session state key to avoid conflicts)
        db_types = ["PostgreSQL", "MySQL", "Oracle", "DynamoDB", "Athena"]
        
        # Use a different approach to avoid session state conflicts
        if 'selected_db_type' not in st.session_state:
            st.session_state.selected_db_type = "PostgreSQL"
        
        selected_db_type = st.selectbox(
            "Database Type:",
            db_types,
            index=db_types.index(st.session_state.selected_db_type),
            key="wizard_db_type"
        )
        
        # Update session state
        st.session_state.selected_db_type = selected_db_type
        
        # Connection form
        with st.form("database_connection_form"):
            st.subheader(f"📋 {selected_db_type} Connection Details")
            
            if selected_db_type == "PostgreSQL":
                host = st.text_input("Host", value=settings.postgres_host or "localhost")
                port = st.number_input("Port", value=settings.postgres_port or 5432, min_value=1, max_value=65535)
                database = st.text_input("Database", value=settings.postgres_db or "")
                username = st.text_input("Username", value=settings.postgres_user or "")
                password = st.text_input("Password", type="password")
                
            elif selected_db_type == "MySQL":
                host = st.text_input("Host", value=settings.mysql_host or "localhost")
                port = st.number_input("Port", value=settings.mysql_port or 3306, min_value=1, max_value=65535)
                database = st.text_input("Database", value=settings.mysql_db or "")
                username = st.text_input("Username", value=settings.mysql_user or "")
                password = st.text_input("Password", type="password")
                
            elif selected_db_type == "Oracle":
                host = st.text_input("Host", value=settings.oracle_host or "localhost")
                port = st.number_input("Port", value=settings.oracle_port or 1521, min_value=1, max_value=65535)
                service = st.text_input("Service Name", value=settings.oracle_service or "")
                username = st.text_input("Username", value=settings.oracle_user or "")
                password = st.text_input("Password", type="password")
                
            elif selected_db_type == "DynamoDB":
                region = st.text_input("AWS Region", value="us-east-1")
                access_key = st.text_input("AWS Access Key ID")
                secret_key = st.text_input("AWS Secret Access Key", type="password")
                
            else:  # Athena
                region = st.text_input("AWS Region", value="us-east-1")
                access_key = st.text_input("AWS Access Key ID")
                secret_key = st.text_input("AWS Secret Access Key", type="password")
                s3_output = st.text_input("S3 Output Location", value="s3://aws-athena-query-results-default/")
            
            # Test connection button
            col1, col2 = st.columns([1, 1])
            with col1:
                test_connection = st.form_submit_button("🔍 Test Connection", use_container_width=True)
            with col2:
                connect_and_continue = st.form_submit_button("🚀 Connect & Continue", type="primary", use_container_width=True)
        
        # Handle connection testing
        if test_connection or connect_and_continue:
            success = self._test_database_connection(selected_db_type, locals())
            
            if success:
                st.success("✅ Connection successful!")
                if connect_and_continue:
                    # Store connection details
                    st.session_state.connection_details = {
                        'db_type': selected_db_type,
                        'params': {k: v for k, v in locals().items() 
                                 if k not in ['test_connection', 'connect_and_continue', 'selected_db_type', 'success']}
                    }
                    st.session_state.connected = True
                    st.session_state.wizard_step = 1
                    st.rerun()
            else:
                st.error("❌ Connection failed. Please check your credentials and try again.")
    
    def _step_schema_analysis(self):
        """Step 2: Schema Analysis"""
        st.header("📊 Step 2: Database Schema Analysis")
        st.write("Analyzing your database structure...")
        
        if 'schema_analysis_done' not in st.session_state:
            with st.spinner("🔍 Analyzing database schema..."):
                try:
                    # Get schema information
                    db_type = st.session_state.connection_details['db_type']
                    
                    if db_type in ["PostgreSQL", "MySQL", "Oracle"]:
                        # Add option to include views
                        include_views = st.checkbox(
                            "Include database views", 
                            value=False,
                            help="Check this if you want to include database views along with tables"
                        )
                        schema_info = db_manager.get_table_schema(include_views=include_views)
                    elif db_type == "DynamoDB":
                        tables = nosql_manager.get_dynamodb_tables()
                        schema_info = {}
                        for table in tables[:10]:  # Limit for demo
                            schema_info[table] = nosql_manager.get_dynamodb_table_schema(table)
                    else:  # Athena
                        databases = nosql_manager.get_athena_databases()
                        schema_info = {}
                        if databases:
                            tables = nosql_manager.get_athena_tables(databases[0])
                            for table in tables[:10]:
                                schema_info[table] = nosql_manager.get_athena_table_schema(databases[0], table)
                    
                    st.session_state.schema_info = schema_info
                    st.session_state.schema_analysis_done = True
                    
                except Exception as e:
                    st.error(f"❌ Schema analysis failed: {str(e)}")
                    return
        
        # Show schema summary
        schema_info = st.session_state.schema_info
        
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("📋 User Tables", len(schema_info))
        with col2:
            total_columns = sum(len(table.get('columns', [])) for table in schema_info.values())
            st.metric("📊 Total Columns", total_columns)
        with col3:
            avg_columns = total_columns / len(schema_info) if schema_info else 0
            st.metric("📈 Avg Columns/Table", f"{avg_columns:.1f}")
        
        # Show all tables in an expandable view
        with st.expander("🔍 All Tables & Columns", expanded=True):
            # Create tabs for better organization if many tables
            if len(schema_info) > 10:
                # Group tables into tabs
                table_names = list(schema_info.keys())
                tab_size = 10
                tabs = []
                for i in range(0, len(table_names), tab_size):
                    end_idx = min(i + tab_size, len(table_names))
                    tabs.append(f"Tables {i+1}-{end_idx}")
                
                tab_objects = st.tabs(tabs)
                
                for tab_idx, tab in enumerate(tab_objects):
                    with tab:
                        start_idx = tab_idx * tab_size
                        end_idx = min(start_idx + tab_size, len(table_names))
                        
                        for table_name in table_names[start_idx:end_idx]:
                            table_info = schema_info[table_name]
                            self._render_table_info(table_name, table_info)
            else:
                # Show all tables directly
                for table_name, table_info in schema_info.items():
                    self._render_table_info(table_name, table_info)
        
        # Complexity analysis
        high_dim_tables = [name for name, info in schema_info.items() 
                          if len(info.get('columns', [])) > 50]
        
        if high_dim_tables:
            st.warning(f"⚠️ Found {len(high_dim_tables)} high-dimensional tables (>50 columns): {', '.join(high_dim_tables[:3])}{'...' if len(high_dim_tables) > 3 else ''}. Enhanced semantic layer recommended.")
        else:
            st.success("✅ Schema complexity looks manageable. All semantic layer options will work well.")
        
        # Continue button
        if st.button("➡️ Continue to Semantic Setup", type="primary", use_container_width=True):
            st.session_state.wizard_step = 2
            st.rerun()
    
    def _render_table_info(self, table_name: str, table_info: Dict[str, Any]):
        """Render information for a single table"""
        columns = table_info.get('columns', [])
        
        with st.container():
            col1, col2 = st.columns([3, 1])
            
            with col1:
                st.write(f"**📋 {table_name}**")
                if columns:
                    # Show first 10 columns with their types
                    col_display = []
                    for col in columns[:10]:
                        col_name = col.get('name', 'unknown')
                        col_type = str(col.get('type', 'unknown'))
                        nullable = "NULL" if col.get('nullable', True) else "NOT NULL"
                        pk = " 🔑" if col.get('primary_key', False) else ""
                        col_display.append(f"• {col_name} ({col_type}) {nullable}{pk}")
                    
                    st.write("\n".join(col_display))
                    
                    if len(columns) > 10:
                        st.write(f"... and {len(columns) - 10} more columns")
                else:
                    st.write("No column information available")
            
            with col2:
                st.metric("Columns", len(columns))
                
                # Show foreign keys if any
                fks = table_info.get('foreign_keys', [])
                if fks:
                    st.metric("Foreign Keys", len(fks))
            
            st.write("")  # Spacing
    
    def _step_semantic_setup(self):
        """Step 3: Semantic Layer Setup"""
        st.header("🧠 Step 3: Build Enhanced Semantic Layer")
        st.write("Create business-friendly metadata for better query understanding.")
        
        # Semantic layer options
        semantic_method = st.radio(
            "Choose your approach:",
            [
                "🤖 Automatic (AI generates business metadata)",
                "✏️ Manual (Upload your own metadata)",
                "🔄 Hybrid (AI generates, you edit)"
            ],
            key="semantic_method_choice"
        )
        
        if "🤖 Automatic" in semantic_method:
            self._render_automatic_semantic_setup()
        elif "✏️ Manual" in semantic_method:
            self._render_manual_semantic_setup()
        else:
            self._render_hybrid_semantic_setup()
    
    def _render_automatic_semantic_setup(self):
        """Render automatic semantic setup"""
        st.subheader("🤖 Automatic Semantic Layer Generation")
        
        with st.form("automatic_semantic_form"):
            col1, col2 = st.columns(2)
            
            with col1:
                business_domain = st.selectbox(
                    "Primary Business Domain:",
                    ["General", "E-commerce", "Finance", "Healthcare", "Manufacturing", "Education", "Real Estate"]
                )
                
                include_examples = st.checkbox("Generate example values", value=True)
                
            with col2:
                schema_info = st.session_state.schema_info
                total_columns = sum(len(table.get('columns', [])) for table in schema_info.values())
                
                st.metric("Tables to Process", len(schema_info))
                st.metric("Columns to Process", total_columns)
                
                estimated_time = max(1, total_columns // 100)
                st.info(f"⏱️ Estimated time: ~{estimated_time} minutes")
            
            # Sample queries section
            st.write("**Sample Query-SQL Pairs (Optional)**")
            st.info("Adding sample queries helps AI understand your specific use cases")
            
            if 'sample_queries' not in st.session_state:
                st.session_state.sample_queries = []
            
            # Simple sample query input
            sample_question = st.text_input("Example Question:", placeholder="e.g., Show top 10 customers by revenue")
            sample_sql = st.text_area("Corresponding SQL:", placeholder="e.g., SELECT customer_name, SUM(revenue) FROM...", height=100)
            
            if st.form_submit_button("Add Sample Query"):
                if sample_question and sample_sql:
                    st.session_state.sample_queries.append({
                        'question': sample_question,
                        'sql': sample_sql
                    })
                    st.success("Sample query added!")
            
            # Show existing sample queries
            if st.session_state.sample_queries:
                st.write(f"**Added Queries ({len(st.session_state.sample_queries)}):**")
                for i, query in enumerate(st.session_state.sample_queries):
                    st.write(f"{i+1}. {query['question']}")
            
            # Generate button
            generate_semantic = st.form_submit_button("🚀 Generate Semantic Layer", type="primary")
        
        if generate_semantic:
            self._execute_automatic_semantic_generation(business_domain, include_examples)
    
    def _render_manual_semantic_setup(self):
        """Render manual semantic setup"""
        st.subheader("✏️ Manual Semantic Layer Setup")
        
        # Step 1: Download template
        st.write("**Step 1: Download Template**")
        template_df = enhanced_semantic_layer.export_enhanced_metadata_template(st.session_state.schema_info)
        
        csv_template = template_df.to_csv(index=False)
        st.download_button(
            label="📥 Download Metadata Template",
            data=csv_template,
            file_name=f"semantic_metadata_template_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
        
        st.info(f"📊 Template contains {len(template_df)} rows for all your columns")
        
        # Step 2: Upload completed template
        st.write("**Step 2: Upload Completed Template**")
        uploaded_file = st.file_uploader(
            "Upload your completed metadata CSV:",
            type=['csv'],
            help="Fill out the template and upload it here"
        )
        
        if uploaded_file is not None:
            try:
                uploaded_df = pd.read_csv(uploaded_file)
                
                # Validate
                required_columns = ['table_name', 'real_col_name', 'alias_name', 'type', 'description']
                missing_columns = [col for col in required_columns if col not in uploaded_df.columns]
                
                if missing_columns:
                    st.error(f"❌ Missing required columns: {', '.join(missing_columns)}")
                else:
                    st.success(f"✅ Valid metadata file with {len(uploaded_df)} rows")
                    
                    # Preview
                    with st.expander("📊 Data Preview"):
                        st.dataframe(uploaded_df.head(10))
                    
                    if st.button("🏗️ Build Semantic Layer", type="primary", use_container_width=True):
                        self._execute_manual_semantic_build(uploaded_df)
                        
            except Exception as e:
                st.error(f"❌ Error reading file: {str(e)}")
    
    def _render_hybrid_semantic_setup(self):
        """Render hybrid semantic setup"""
        st.subheader("🔄 Hybrid Semantic Layer Setup")
        
        # Step 1: Generate initial metadata
        if 'generated_metadata' not in st.session_state:
            if st.button("🤖 Generate Initial Metadata", type="primary", use_container_width=True):
                with st.spinner("🤖 AI is generating metadata..."):
                    try:
                        generated_metadata = enhanced_semantic_layer.generate_automatic_enhanced_metadata(
                            st.session_state.schema_info
                        )
                        st.session_state.generated_metadata = generated_metadata
                        st.success("✅ Initial metadata generated!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"❌ Generation failed: {str(e)}")
        else:
            # Step 2: Edit generated metadata
            st.write("**Edit AI-Generated Metadata:**")
            
            # Convert to editable format
            edit_df = self._convert_metadata_to_dataframe(
                st.session_state.generated_metadata, 
                st.session_state.schema_info
            )
            
            # Show editable table (simplified for better performance)
            st.write("📝 Review and edit the business names and descriptions:")
            
            # Show first few rows for editing
            sample_size = min(20, len(edit_df))
            st.info(f"Showing first {sample_size} rows for editing. Full semantic layer will be built with all data.")
            
            edited_sample = st.data_editor(
                edit_df.head(sample_size),
                use_container_width=True,
                column_config={
                    "alias_name": st.column_config.TextColumn("Business Name"),
                    "description": st.column_config.TextColumn("Description"),
                    "domain": st.column_config.SelectboxColumn(
                        "Domain", 
                        options=["general", "sales", "customer", "product", "finance", "marketing", "operations"]
                    )
                }
            )
            
            if st.button("🏗️ Build Hybrid Semantic Layer", type="primary", use_container_width=True):
                # Use the full generated metadata (not just the edited sample)
                self._execute_hybrid_semantic_build(edit_df)
    
    def _step_ready_to_query(self):
        """Step 4: Ready to Query"""
        st.header("🎉 Step 4: Ready to Query!")
        st.success("✅ Your GenBI system is fully configured and ready to use!")
        
        # Summary
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("🔗 Database", st.session_state.connection_details['db_type'])
        with col2:
            st.metric("📋 Tables", len(st.session_state.schema_info))
        with col3:
            method = st.session_state.get('semantic_method', 'Unknown')
            st.metric("🧠 Semantic Layer", method)
        
        # Quick start guide
        with st.expander("🚀 Quick Start Guide", expanded=True):
            st.write("""
            **You can now ask questions in natural language:**
            
            📊 **Sales Analysis:**
            - "Show me total sales by month for the last year"
            - "What are the top 10 products by revenue?"
            
            👥 **Customer Insights:**
            - "Find customers who haven't purchased in 6 months"
            - "Show customer lifetime value by segment"
            
            📈 **Performance Metrics:**
            - "Compare sales performance across regions"
            - "What's the average order value by customer type?"
            """)
        
        # Start querying button
        if st.button("🚀 Start Querying Your Data", type="primary", use_container_width=True):
            st.session_state.wizard_completed = True
            st.session_state.show_query_interface = True
            st.rerun()
    
    def _test_database_connection(self, db_type: str, params: dict) -> bool:
        """Test database connection"""
        try:
            if db_type == "PostgreSQL":
                # Update settings temporarily for connection test
                original_settings = {
                    'host': settings.postgres_host,
                    'port': settings.postgres_port,
                    'db': settings.postgres_db,
                    'user': settings.postgres_user,
                    'password': settings.postgres_password
                }
                
                # Temporarily update settings
                settings.postgres_host = params.get('host', 'localhost')
                settings.postgres_port = params.get('port', 5432)
                settings.postgres_db = params.get('database', '')
                settings.postgres_user = params.get('username', '')
                settings.postgres_password = params.get('password', '')
                
                success = db_manager.connect("postgresql")
                
                # Restore original settings
                for key, value in original_settings.items():
                    setattr(settings, f'postgres_{key}', value)
                
                return success
                
            elif db_type == "MySQL":
                settings.mysql_host = params.get('host', 'localhost')
                settings.mysql_port = params.get('port', 3306)
                settings.mysql_db = params.get('database', '')
                settings.mysql_user = params.get('username', '')
                settings.mysql_password = params.get('password', '')
                
                return db_manager.connect("mysql")
                
            elif db_type == "Oracle":
                settings.oracle_host = params.get('host', 'localhost')
                settings.oracle_port = params.get('port', 1521)
                settings.oracle_service = params.get('service', '')
                settings.oracle_user = params.get('username', '')
                settings.oracle_password = params.get('password', '')
                
                return db_manager.connect("oracle")
                
            elif db_type == "DynamoDB":
                return nosql_manager.connect_dynamodb(
                    region_name=params.get('region', 'us-east-1'),
                    aws_access_key_id=params.get('access_key', ''),
                    aws_secret_access_key=params.get('secret_key', '')
                )
                
            else:  # Athena
                return nosql_manager.connect_athena(
                    region_name=params.get('region', 'us-east-1'),
                    aws_access_key_id=params.get('access_key', ''),
                    aws_secret_access_key=params.get('secret_key', ''),
                    s3_output_location=params.get('s3_output', 's3://aws-athena-query-results-default/')
                )
                
        except Exception as e:
            logger.error(f"Connection test failed: {str(e)}")
            return False
    
    def _execute_automatic_semantic_generation(self, business_domain: str, include_examples: bool):
        """Execute automatic semantic generation with detailed progress"""
        try:
            schema_info = st.session_state.schema_info
            total_tables = len(schema_info)
            
            # Create progress containers
            progress_bar = st.progress(0)
            status_text = st.empty()
            table_progress = st.empty()
            
            # Track completed tables
            completed_tables = []
            
            def progress_callback(message: str, current: int, total: int):
                # Update progress bar
                progress = current / total if total > 0 else 0
                progress_bar.progress(progress)
                
                # Update status text
                status_text.info(f"🤖 {message}")
                
                # Update table progress display
                if "✅ Completed:" in message:
                    table_name = message.replace("✅ Completed: ", "")
                    completed_tables.append(table_name)
                
                # Show completed tables with checkmarks
                if completed_tables:
                    progress_html = "<div style='background-color: #f8f9fa; padding: 1rem; border-radius: 0.5rem; margin: 1rem 0;'>"
                    progress_html += f"<h4>📊 Progress: {len(completed_tables)}/{total_tables} tables completed</h4>"
                    
                    # Show completed tables in columns
                    cols_per_row = 3
                    for i in range(0, len(completed_tables), cols_per_row):
                        progress_html += "<div style='display: flex; gap: 1rem; margin: 0.5rem 0;'>"
                        for j in range(cols_per_row):
                            if i + j < len(completed_tables):
                                table_name = completed_tables[i + j]
                                progress_html += f"<div style='flex: 1; background-color: #d4edda; padding: 0.5rem; border-radius: 0.3rem; border-left: 3px solid #28a745;'>✅ {table_name}</div>"
                            else:
                                progress_html += "<div style='flex: 1;'></div>"
                        progress_html += "</div>"
                    
                    # Show remaining tables
                    remaining_tables = [name for name in schema_info.keys() if name not in completed_tables]
                    if remaining_tables:
                        progress_html += "<h5>⏳ Remaining tables:</h5>"
                        for i in range(0, len(remaining_tables), cols_per_row):
                            progress_html += "<div style='display: flex; gap: 1rem; margin: 0.5rem 0;'>"
                            for j in range(cols_per_row):
                                if i + j < len(remaining_tables):
                                    table_name = remaining_tables[i + j]
                                    progress_html += f"<div style='flex: 1; background-color: #fff3cd; padding: 0.5rem; border-radius: 0.3rem; border-left: 3px solid #ffc107;'>⏳ {table_name}</div>"
                                else:
                                    progress_html += "<div style='flex: 1;'></div>"
                            progress_html += "</div>"
                    
                    progress_html += "</div>"
                    table_progress.markdown(progress_html, unsafe_allow_html=True)
            
            # Start the generation process
            status_text.info("🚀 Starting automatic semantic layer generation...")
            
            # Generate enhanced metadata with progress tracking
            enhanced_metadata = enhanced_semantic_layer.generate_automatic_enhanced_metadata(
                schema_info, progress_callback=progress_callback
            )
            
            # Get sample queries
            sample_queries = st.session_state.get('sample_queries', [])
            
            # Update status for final step
            status_text.info("🔗 Creating vector embeddings...")
            progress_bar.progress(0.9)
            
            # Create enhanced embeddings
            enhanced_semantic_layer.create_enhanced_schema_embeddings(
                schema_info=schema_info,
                enhanced_metadata=enhanced_metadata,
                sample_queries=sample_queries,
                connection_name="default"
            )
            
            # Complete
            progress_bar.progress(1.0)
            status_text.success("🎉 Automatic semantic layer created successfully!")
            
            # Final summary
            summary_html = f"""
            <div style='background-color: #d4edda; padding: 1.5rem; border-radius: 0.5rem; border-left: 4px solid #28a745; margin: 1rem 0;'>
                <h3>✅ Semantic Layer Generation Complete!</h3>
                <div style='display: flex; gap: 2rem; margin: 1rem 0;'>
                    <div><strong>📋 Tables Processed:</strong> {len(enhanced_metadata)}</div>
                    <div><strong>📊 Columns Enhanced:</strong> {sum(len(table.get('columns', {})) for table in enhanced_metadata.values())}</div>
                    <div><strong>🔍 Sample Queries:</strong> {len(sample_queries)}</div>
                </div>
                <p><strong>🧠 Business Domain:</strong> {business_domain}</p>
                <p><strong>💡 Examples Generated:</strong> {'Yes' if include_examples else 'No'}</p>
            </div>
            """
            table_progress.markdown(summary_html, unsafe_allow_html=True)
            
            # Update session state
            st.session_state.semantic_layer_built = True
            st.session_state.semantic_method = "Automatic"
            st.session_state.wizard_step = 3
            
            # Auto-advance to next step
            st.rerun()
                
        except Exception as e:
            st.error(f"❌ Failed to generate semantic layer: {str(e)}")
            logger.error(f"Automatic semantic generation failed: {str(e)}")
            
            # Show error details
            error_html = f"""
            <div style='background-color: #f8d7da; padding: 1rem; border-radius: 0.5rem; border-left: 4px solid #dc3545; margin: 1rem 0;'>
                <h4>❌ Generation Failed</h4>
                <p><strong>Error:</strong> {str(e)}</p>
                <p><strong>Completed Tables:</strong> {len(completed_tables) if 'completed_tables' in locals() else 0}</p>
                <p>You can try again or switch to Manual/Hybrid mode.</p>
            </div>
            """
            table_progress.markdown(error_html, unsafe_allow_html=True)
    
    def _execute_manual_semantic_build(self, metadata_df: pd.DataFrame):
        """Execute manual semantic build"""
        try:
            with st.spinner("🏗️ Building semantic layer from your metadata..."):
                # Convert DataFrame to enhanced metadata format
                enhanced_metadata = enhanced_semantic_layer.import_enhanced_metadata_from_dataframe(metadata_df)
                
                # Create enhanced embeddings
                enhanced_semantic_layer.create_enhanced_schema_embeddings(
                    schema_info=st.session_state.schema_info,
                    enhanced_metadata=enhanced_metadata,
                    sample_queries=[],
                    connection_name="default"
                )
                
                st.session_state.semantic_layer_built = True
                st.session_state.semantic_method = "Manual"
                st.session_state.wizard_step = 3
                
                st.success("✅ Manual semantic layer created successfully!")
                st.rerun()
                
        except Exception as e:
            st.error(f"❌ Failed to build semantic layer: {str(e)}")
            logger.error(f"Manual semantic build failed: {str(e)}")
    
    def _execute_hybrid_semantic_build(self, metadata_df: pd.DataFrame):
        """Execute hybrid semantic build"""
        try:
            with st.spinner("🔄 Building hybrid semantic layer..."):
                # Convert DataFrame to enhanced metadata format
                enhanced_metadata = enhanced_semantic_layer.import_enhanced_metadata_from_dataframe(metadata_df)
                
                # Create enhanced embeddings
                enhanced_semantic_layer.create_enhanced_schema_embeddings(
                    schema_info=st.session_state.schema_info,
                    enhanced_metadata=enhanced_metadata,
                    sample_queries=[],
                    connection_name="default"
                )
                
                st.session_state.semantic_layer_built = True
                st.session_state.semantic_method = "Hybrid"
                st.session_state.wizard_step = 3
                
                st.success("✅ Hybrid semantic layer created successfully!")
                st.rerun()
                
        except Exception as e:
            st.error(f"❌ Failed to build semantic layer: {str(e)}")
            logger.error(f"Hybrid semantic build failed: {str(e)}")
    
    def _convert_metadata_to_dataframe(self, metadata: Dict[str, Any], schema_info: Dict[str, Any]) -> pd.DataFrame:
        """Convert metadata dictionary to DataFrame"""
        rows = []
        
        for table_name, table_meta in metadata.items():
            if table_name in schema_info:
                for col in schema_info[table_name].get('columns', []):
                    col_name = col.get('name', 'unknown')
                    col_meta = table_meta.get('columns', {}).get(col_name, {})
                    
                    rows.append({
                        'table_name': table_name,
                        'real_col_name': col_name,
                        'alias_name': col_meta.get('alias_name', col_name),
                        'type': str(col.get('type', 'unknown')),
                        'description': col_meta.get('description', ''),
                        'domain': col_meta.get('domain', 'general'),
                        'examples': ', '.join(col_meta.get('examples', [])),
                        'synonyms': ', '.join(col_meta.get('synonyms', [])),
                        'business_rules': col_meta.get('business_rules', '')
                    })
        
        return pd.DataFrame(rows)

# Global instance
setup_wizard = SetupWizard()
