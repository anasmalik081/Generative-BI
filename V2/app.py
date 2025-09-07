import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Dict, Any, List
import logging
import time
from datetime import datetime

# Import our modules
from config.settings import settings
from database.connection_manager import db_manager
from database.nosql_connection_manager import nosql_manager
from semantic_layer.enhanced_semantic_layer import enhanced_semantic_layer
from agents.sql_agent_fixed import improved_sql_agent as sql_agent
from visualization.chart_generator import chart_generator
from ui_components.semantic_builder import semantic_builder_ui

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page configuration
st.set_page_config(
    page_title="GenBI - Natural Language Business Intelligence",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 3rem;
        font-weight: bold;
        text-align: center;
        margin-bottom: 2rem;
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    
    .metric-card {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        border-left: 4px solid #667eea;
    }
    
    .sql-container {
        background-color: #1e1e1e;
        color: #ffffff;
        padding: 1rem;
        border-radius: 0.5rem;
        font-family: 'Courier New', monospace;
    }
    
    .insight-box {
        background-color: #e8f4fd;
        padding: 1.5rem;
        border-radius: 0.5rem;
        border-left: 4px solid #2196f3;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

def initialize_session_state():
    """Initialize session state variables"""
    if 'connected' not in st.session_state:
        st.session_state.connected = False
    if 'query_history' not in st.session_state:
        st.session_state.query_history = []
    if 'current_result' not in st.session_state:
        st.session_state.current_result = None
    if 'schema_loaded' not in st.session_state:
        st.session_state.schema_loaded = False
    if 'semantic_layer_built' not in st.session_state:
        st.session_state.semantic_layer_built = False
    if 'semantic_method' not in st.session_state:
        st.session_state.semantic_method = None
    if 'db_type' not in st.session_state:
        st.session_state.db_type = "PostgreSQL"
    if 'sample_queries' not in st.session_state:
        st.session_state.sample_queries = []

def sidebar_database_connection():
    """Handle database connection in sidebar"""
    st.sidebar.header("🔗 Database Connection")
    
    db_type = st.sidebar.selectbox(
        "Database Type",
        ["PostgreSQL", "MySQL", "Oracle", "DynamoDB", "Athena"],
        key="db_type"
    )
    
    with st.sidebar.expander("Connection Settings", expanded=not st.session_state.connected):
        if db_type == "PostgreSQL":
            host = st.text_input("Host", value=settings.postgres_host, key="pg_host")
            port = st.number_input("Port", value=settings.postgres_port, key="pg_port")
            database = st.text_input("Database", value=settings.postgres_db, key="pg_db")
            username = st.text_input("Username", value=settings.postgres_user, key="pg_user")
            password = st.text_input("Password", type="password", key="pg_pass")
        elif db_type == "MySQL":
            host = st.text_input("Host", value=settings.mysql_host, key="my_host")
            port = st.number_input("Port", value=settings.mysql_port, key="my_port")
            database = st.text_input("Database", value=settings.mysql_db, key="my_db")
            username = st.text_input("Username", value=settings.mysql_user, key="my_user")
            password = st.text_input("Password", type="password", key="my_pass")
        elif db_type == "Oracle":
            host = st.text_input("Host", value=settings.oracle_host, key="or_host")
            port = st.number_input("Port", value=settings.oracle_port, key="or_port")
            service = st.text_input("Service", value=settings.oracle_service, key="or_service")
            username = st.text_input("Username", value=settings.oracle_user, key="or_user")
            password = st.text_input("Password", type="password", key="or_pass")
        elif db_type == "DynamoDB":
            region = st.text_input("AWS Region", value="us-east-1", key="dynamo_region")
            access_key = st.text_input("AWS Access Key ID", key="dynamo_access_key")
            secret_key = st.text_input("AWS Secret Access Key", type="password", key="dynamo_secret_key")
        else:  # Athena
            region = st.text_input("AWS Region", value="us-east-1", key="athena_region")
            access_key = st.text_input("AWS Access Key ID", key="athena_access_key")
            secret_key = st.text_input("AWS Secret Access Key", type="password", key="athena_secret_key")
            s3_output = st.text_input("S3 Output Location", value="s3://aws-athena-query-results-default/", key="athena_s3_output")
    
    col1, col2 = st.sidebar.columns(2)
    
    with col1:
        if st.button("Connect", type="primary", use_container_width=True):
            with st.spinner("Connecting to database..."):
                try:
                    if db_type in ["PostgreSQL", "MySQL", "Oracle"]:
                        success = db_manager.connect(db_type.lower())
                    elif db_type == "DynamoDB":
                        success = nosql_manager.connect_dynamodb(
                            region_name=region,
                            aws_access_key_id=access_key,
                            aws_secret_access_key=secret_key
                        )
                    else:  # Athena
                        success = nosql_manager.connect_athena(
                            region_name=region,
                            aws_access_key_id=access_key,
                            aws_secret_access_key=secret_key,
                            s3_output_location=s3_output
                        )
                    
                    if success:
                        st.session_state.connected = True
                        st.session_state.db_type = db_type
                        st.success("Connected successfully!")
                        
                        # Load schema
                        with st.spinner("Loading database schema..."):
                            if db_type in ["PostgreSQL", "MySQL", "Oracle"]:
                                schema_info = db_manager.get_table_schema()
                            elif db_type == "DynamoDB":
                                # For DynamoDB, we'll handle schema differently
                                tables = nosql_manager.get_dynamodb_tables()
                                schema_info = {}
                                for table in tables[:5]:  # Limit to first 5 tables for demo
                                    schema_info[table] = nosql_manager.get_dynamodb_table_schema(table)
                            else:  # Athena
                                databases = nosql_manager.get_athena_databases()
                                schema_info = {}
                                if databases:
                                    tables = nosql_manager.get_athena_tables(databases[0])
                                    for table in tables[:5]:  # Limit to first 5 tables
                                        schema_info[table] = nosql_manager.get_athena_table_schema(databases[0], table)
                            
                            st.session_state.schema_info = schema_info
                            st.session_state.schema_loaded = True
                            st.success("Schema loaded!")
                    else:
                        st.error("Connection failed!")
                except Exception as e:
                    st.error(f"Connection error: {str(e)}")
    
    with col2:
        if st.button("Disconnect", use_container_width=True):
            if st.session_state.db_type in ["PostgreSQL", "MySQL", "Oracle"]:
                db_manager.close_connections()
            else:
                # Reset NoSQL connections
                nosql_manager.connections.clear()
            
            st.session_state.connected = False
            st.session_state.schema_loaded = False
            st.session_state.semantic_layer_built = False
            st.success("Disconnected!")
    
    # Connection status
    if st.session_state.connected:
        st.sidebar.success(f"✅ Connected to {st.session_state.db_type}")
        
        # Show semantic layer status
        if st.session_state.semantic_layer_built:
            st.sidebar.success(f"🧠 Semantic Layer: {st.session_state.semantic_method}")
        else:
            st.sidebar.warning("⚠️ Semantic layer not built")
    else:
        st.sidebar.error("❌ Not Connected")

def sidebar_query_history():
    """Display query history in sidebar"""
    st.sidebar.header("📝 Query History")
    
    if st.session_state.query_history:
        for i, query_item in enumerate(reversed(st.session_state.query_history[-10:])):
            with st.sidebar.expander(f"Query {len(st.session_state.query_history) - i}"):
                st.write(f"**Query:** {query_item['query'][:100]}...")
                st.write(f"**Time:** {query_item['timestamp']}")
                if st.button(f"Rerun", key=f"rerun_{i}"):
                    st.session_state.current_query = query_item['query']
                    st.rerun()
    else:
        st.sidebar.info("No queries yet")

def main_interface():
    """Main application interface"""
    st.markdown('<h1 class="main-header">GenBI - Natural Language Business Intelligence</h1>', 
                unsafe_allow_html=True)
    
    if not st.session_state.connected:
        st.warning("⚠️ Please connect to a database first using the sidebar.")
        return
    
    # Show semantic layer builder if schema is loaded but semantic layer not built
    if st.session_state.schema_loaded and not st.session_state.semantic_layer_built:
        st.info("🧠 Your database schema is loaded. Now let's build an enhanced semantic layer for better query understanding.")
        
        # Render semantic builder
        semantic_builder_ui.render_semantic_builder(
            st.session_state.schema_info, 
            connection_name="default"
        )
        
        # Don't show query interface until semantic layer is built
        return
    
    if not st.session_state.semantic_layer_built:
        st.warning("⚠️ Please build the semantic layer first to enable intelligent querying.")
        return
    
    # Query input
    st.header("🤖 Ask Your Data")
    
    col1, col2 = st.columns([4, 1])
    
    with col1:
        user_query = st.text_area(
            "Enter your question in natural language:",
            placeholder="e.g., Show me the top 10 customers by revenue this year",
            height=100,
            key="query_input"
        )
    
    with col2:
        st.write("")  # Spacing
        st.write("")  # Spacing
        execute_query = st.button("🚀 Execute Query", type="primary", use_container_width=True)
        
        if st.button("💡 Example Queries", use_container_width=True):
            examples = [
                "Show me total sales by month for the last year",
                "What are the top 5 products by revenue?",
                "Find customers who haven't made a purchase in 6 months",
                "Compare sales performance across different regions",
                "Show me the average order value by customer segment"
            ]
            st.info("Example queries:\n" + "\n".join([f"• {ex}" for ex in examples]))
    
    # Execute query
    if execute_query and user_query.strip():
        execute_natural_language_query(user_query.strip())
    
    # Display results
    if st.session_state.current_result:
        display_query_results(st.session_state.current_result)

def execute_natural_language_query(user_query: str):
    """Execute natural language query and store results"""
    try:
        with st.spinner("🧠 Processing your query..."):
            # Add debug info
            st.info(f"🔍 Analyzing query: {user_query}")
            
            # Use enhanced semantic search
            relevant_schema = enhanced_semantic_layer.search_enhanced_schema(
                user_query, 
                connection_name="default", 
                top_k=15
            )
            
            # Process query through SQL agent
            result = sql_agent.process_query(user_query)
            
            # Debug information
            st.info(f"📝 Generated SQL: {result.get('generated_sql', 'None')}")
            if result.get('error_message'):
                st.error(f"⚠️ Error details: {result['error_message']}")
            
            # Add to history
            st.session_state.query_history.append({
                'query': user_query,
                'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'result': result
            })
            
            # Store current result
            st.session_state.current_result = result
            
            if result.get('error_message'):
                st.error(f"❌ Error: {result['error_message']}")
            else:
                execution_result = result.get('execution_result')
                if execution_result is not None and not execution_result.empty:
                    st.success(f"✅ Query executed successfully! Retrieved {len(execution_result)} rows.")
                else:
                    st.warning("⚠️ Query executed but returned no data.")
                
    except Exception as e:
        st.error(f"❌ Execution failed: {str(e)}")
        logger.error(f"Query execution failed: {str(e)}")
        # Show more detailed error information
        import traceback
        st.code(traceback.format_exc())

def display_query_results(result: Dict[str, Any]):
    """Display comprehensive query results"""
    if not result:
        return
    
    # Create tabs for different views
    tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🔍 Data", "💻 SQL Query", "🧠 Insights"])
    
    with tab1:
        display_dashboard(result)
    
    with tab2:
        display_data_table(result)
    
    with tab3:
        display_sql_query(result)
    
    with tab4:
        display_insights(result)

def display_dashboard(result: Dict[str, Any]):
    """Display interactive dashboard"""
    st.header("📊 Interactive Dashboard")
    
    df = result.get('execution_result')
    if df is not None and not df.empty:
        # Generate multiple charts
        charts = chart_generator.create_dashboard(df, result['user_query'])
        
        # Display charts in a grid
        if len(charts) == 1:
            st.plotly_chart(charts[0], use_container_width=True)
        elif len(charts) == 2:
            col1, col2 = st.columns(2)
            with col1:
                st.plotly_chart(charts[0], use_container_width=True)
            with col2:
                st.plotly_chart(charts[1], use_container_width=True)
        else:
            # First chart full width
            st.plotly_chart(charts[0], use_container_width=True)
            
            # Remaining charts in columns
            if len(charts) > 1:
                cols = st.columns(2)
                for i, chart in enumerate(charts[1:3]):
                    with cols[i % 2]:
                        st.plotly_chart(chart, use_container_width=True)
        
        # Data summary metrics
        st.subheader("📈 Key Metrics")
        display_key_metrics(df)
        
    else:
        st.info("No data to visualize")

def display_key_metrics(df: pd.DataFrame):
    """Display key metrics from the data"""
    if df.empty:
        return
    
    cols = st.columns(4)
    
    with cols[0]:
        st.markdown(
            f'<div class="metric-card"><h3>{len(df):,}</h3><p>Total Rows</p></div>',
            unsafe_allow_html=True
        )
    
    with cols[1]:
        st.markdown(
            f'<div class="metric-card"><h3>{len(df.columns)}</h3><p>Columns</p></div>',
            unsafe_allow_html=True
        )
    
    # Numeric columns metrics
    numeric_cols = df.select_dtypes(include=['number']).columns
    if len(numeric_cols) > 0:
        first_numeric = df[numeric_cols[0]]
        
        with cols[2]:
            avg_val = first_numeric.mean()
            st.markdown(
                f'<div class="metric-card"><h3>{avg_val:,.2f}</h3><p>Avg {numeric_cols[0]}</p></div>',
                unsafe_allow_html=True
            )
        
        with cols[3]:
            max_val = first_numeric.max()
            st.markdown(
                f'<div class="metric-card"><h3>{max_val:,.2f}</h3><p>Max {numeric_cols[0]}</p></div>',
                unsafe_allow_html=True
            )

def display_data_table(result: Dict[str, Any]):
    """Display data table with filtering and sorting"""
    st.header("🔍 Data Explorer")
    
    df = result.get('execution_result')
    if df is not None and not df.empty:
        # Data info
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Rows", len(df))
        with col2:
            st.metric("Columns", len(df.columns))
        with col3:
            st.metric("Memory Usage", f"{df.memory_usage(deep=True).sum() / 1024:.1f} KB")
        
        # Column selection
        selected_columns = st.multiselect(
            "Select columns to display:",
            df.columns.tolist(),
            default=df.columns.tolist()[:10]  # Show first 10 columns by default
        )
        
        if selected_columns:
            display_df = df[selected_columns]
            
            # Filtering options
            with st.expander("🔧 Filter Data"):
                filter_column = st.selectbox("Filter by column:", ["None"] + selected_columns)
                if filter_column != "None":
                    if df[filter_column].dtype == 'object':
                        unique_values = df[filter_column].unique()
                        selected_values = st.multiselect(f"Select {filter_column} values:", unique_values)
                        if selected_values:
                            display_df = display_df[display_df[filter_column].isin(selected_values)]
                    else:
                        min_val, max_val = float(df[filter_column].min()), float(df[filter_column].max())
                        range_vals = st.slider(f"Select {filter_column} range:", min_val, max_val, (min_val, max_val))
                        display_df = display_df[
                            (display_df[filter_column] >= range_vals[0]) & 
                            (display_df[filter_column] <= range_vals[1])
                        ]
            
            # Display table
            st.dataframe(display_df, use_container_width=True, height=400)
            
            # Download option
            csv = display_df.to_csv(index=False)
            st.download_button(
                label="📥 Download CSV",
                data=csv,
                file_name=f"query_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                mime="text/csv"
            )
        else:
            st.warning("Please select at least one column to display")
    else:
        st.info("No data to display")

def display_sql_query(result: Dict[str, Any]):
    """Display SQL query with syntax highlighting"""
    st.header("💻 Generated SQL Query")
    
    sql_query = result.get('generated_sql', '')
    if sql_query:
        # Confidence score
        confidence = result.get('confidence_score', 0)
        confidence_color = "green" if confidence > 0.7 else "orange" if confidence > 0.4 else "red"
        
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"**Confidence Score:** <span style='color: {confidence_color}'>{confidence:.2f}</span>", 
                       unsafe_allow_html=True)
        with col2:
            if st.button("📋 Copy SQL", use_container_width=True):
                st.code(sql_query, language='sql')
        
        # SQL query display
        st.markdown(
            f'<div class="sql-container"><pre><code>{sql_query}</code></pre></div>',
            unsafe_allow_html=True
        )
        
        # Query explanation
        with st.expander("🔍 Query Explanation"):
            st.write("**Original Question:**", result.get('user_query', ''))
            
            relevant_schema = result.get('relevant_schema', [])
            if relevant_schema:
                st.write("**Relevant Schema Elements:**")
                for item in relevant_schema[:5]:  # Show top 5
                    metadata = item.get('metadata', {})
                    if metadata.get('type') == 'table':
                        st.write(f"• Table: {metadata.get('table')}")
                    elif metadata.get('type') == 'column':
                        st.write(f"• Column: {metadata.get('table')}.{metadata.get('column')} ({metadata.get('data_type')})")
    else:
        st.info("No SQL query generated")

def display_insights(result: Dict[str, Any]):
    """Display AI-generated insights"""
    st.header("🧠 AI-Generated Insights")
    
    df = result.get('execution_result')
    user_query = result.get('user_query', '')
    sql_query = result.get('generated_sql', '')
    
    if df is not None and not df.empty:
        with st.spinner("🤖 Generating insights..."):
            insights = chart_generator.generate_insights(df, user_query, sql_query)
        
        st.markdown(
            f'<div class="insight-box">{insights}</div>',
            unsafe_allow_html=True
        )
        
        # Additional statistical insights
        with st.expander("📊 Statistical Summary"):
            # Numeric columns summary
            numeric_cols = df.select_dtypes(include=['number']).columns
            if len(numeric_cols) > 0:
                st.write("**Numeric Columns Summary:**")
                st.dataframe(df[numeric_cols].describe())
            
            # Categorical columns summary
            categorical_cols = df.select_dtypes(include=['object']).columns
            if len(categorical_cols) > 0:
                st.write("**Categorical Columns Summary:**")
                for col in categorical_cols[:3]:  # Show first 3 categorical columns
                    st.write(f"**{col}:** {df[col].nunique()} unique values")
                    if df[col].nunique() <= 10:
                        st.write(df[col].value_counts().head())
    else:
        st.info("No data available for insights generation")

def main():
    """Main application entry point"""
    initialize_session_state()
    
    # Sidebar
    sidebar_database_connection()
    sidebar_query_history()
    
    # Main interface
    main_interface()
    
    # Footer
    st.markdown("---")
    st.markdown(
        "**GenBI** - Powered by LangChain, LangGraph, Groq, and Streamlit | "
        "Built for intelligent data exploration"
    )

if __name__ == "__main__":
    main()
