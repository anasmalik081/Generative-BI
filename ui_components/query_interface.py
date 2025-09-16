import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from typing import Dict, Any, List
import logging
from datetime import datetime
from agents.enterprise_sql_agent import enterprise_sql_agent as sql_agent
from visualization.chart_generator import chart_generator

logger = logging.getLogger(__name__)

class QueryInterface:
    def __init__(self):
        pass
    
    def render_query_interface(self):
        """Render the main query interface"""
        # Header
        st.markdown('<h1 class="main-header">🤖 Ask Your Data Anything</h1>', 
                    unsafe_allow_html=True)
        
        # Connection status bar
        self._render_status_bar()
        
        # Query input section
        self._render_query_input()
        
        # Results section
        if st.session_state.get('current_result'):
            self._render_results()
    
    def _render_status_bar(self):
        """Render connection and system status"""
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            db_type = st.session_state.get('connection_details', {}).get('db_type', 'Unknown')
            st.success(f"🔗 Connected: {db_type}")
        
        with col2:
            table_count = len(st.session_state.get('schema_info', {}))
            st.info(f"📋 Tables: {table_count}")
        
        with col3:
            semantic_method = st.session_state.get('semantic_method', 'Unknown')
            st.info(f"🧠 Semantic: {semantic_method}")
        
        with col4:
            query_count = len(st.session_state.get('query_history', []))
            st.info(f"📊 Queries: {query_count}")
        
        # Settings and reset options
        with st.expander("⚙️ Settings & Options"):
            col1, col2, col3 = st.columns(3)
            
            with col1:
                if st.button("🔄 Reconnect Database", use_container_width=True):
                    self._reset_to_wizard()
            
            with col2:
                if st.button("🧠 Rebuild Semantic Layer", use_container_width=True):
                    st.session_state.wizard_step = 2
                    st.session_state.wizard_completed = False
                    st.session_state.show_query_interface = False
                    st.rerun()
            
            with col3:
                if st.button("📊 View Query History", use_container_width=True):
                    self._show_query_history()
    
    def _render_query_input(self):
        """Render query input section"""
        st.header("💬 Natural Language Query")
        
        # Query input with suggestions
        col1, col2 = st.columns([3, 1])
        
        with col1:
            # Smart suggestions based on schema
            if st.button("💡 Show Query Suggestions"):
                self._show_query_suggestions()
            
            user_query = st.text_area(
                "Ask your question in plain English:",
                placeholder="e.g., Show me the top 10 customers by total revenue this year",
                height=120,
                key="main_query_input"
            )
            
            # Quick action buttons
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                if st.button("📈 Sales Analysis", use_container_width=True):
                    st.session_state.main_query_input = "Show me total sales by month for the last year"
                    st.rerun()
            
            with col_b:
                if st.button("👥 Customer Insights", use_container_width=True):
                    st.session_state.main_query_input = "What are the top 10 customers by revenue?"
                    st.rerun()
            
            with col_c:
                if st.button("📊 Product Performance", use_container_width=True):
                    st.session_state.main_query_input = "Show me products with highest profit margins"
                    st.rerun()
        
        with col2:
            st.write("") # Spacing
            st.write("") # Spacing
            st.write("") # Additional spacing for better alignment
            
            # Execute button with better styling
            execute_query = st.button(
                "🚀 Execute Query", 
                type="primary", 
                use_container_width=True
            )
            
            st.write("") # Small spacing
            
            # Query options
            with st.expander("⚙️ Query Options"):
                max_results = st.slider("Max Results", 10, 10000, 1000)
                show_sql = st.checkbox("Show Generated SQL", value=True)
                auto_visualize = st.checkbox("Auto-generate Charts", value=True)
        
        # Execute query
        if execute_query and user_query.strip():
            self._execute_query(user_query.strip(), {
                'max_results': max_results,
                'show_sql': show_sql,
                'auto_visualize': auto_visualize
            })
    
    def _render_results(self):
        """Render query results"""
        result = st.session_state.current_result
        
        if not result:
            return
        
        # Results header
        st.header("📊 Query Results")
        
        # Quick stats
        execution_result = result.get('execution_result')
        if execution_result is not None and not execution_result.empty:
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("📝 Rows Returned", len(execution_result))
            with col2:
                st.metric("📊 Columns", len(execution_result.columns))
            with col3:
                confidence = result.get('confidence_score', 0)
                st.metric("🎯 Confidence", f"{confidence:.2f}")
            with col4:
                st.metric("⏱️ Query Time", "< 1s")  # Could be enhanced with actual timing
        
        # Tabbed results view
        tab1, tab2, tab3, tab4 = st.tabs(["📊 Dashboard", "🔍 Data", "💻 SQL", "🧠 Insights"])
        
        with tab1:
            self._render_dashboard_tab(result)
        
        with tab2:
            self._render_data_tab(result)
        
        with tab3:
            self._render_sql_tab(result)
        
        with tab4:
            self._render_insights_tab(result)
    
    def _render_dashboard_tab(self, result: Dict[str, Any]):
        """Render dashboard tab"""
        st.subheader("📊 Interactive Dashboard")
        
        df = result.get('execution_result')
        if df is not None and not df.empty:
            # Generate multiple charts
            try:
                charts = chart_generator.create_dashboard(df, result['user_query'])
                
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
                    
                    # Additional charts in grid
                    if len(charts) > 1:
                        cols = st.columns(2)
                        for i, chart in enumerate(charts[1:3]):
                            with cols[i % 2]:
                                st.plotly_chart(chart, use_container_width=True)
                
                # Key metrics
                self._render_key_metrics(df)
                
            except Exception as e:
                st.error(f"❌ Visualization error: {str(e)}")
                st.info("📋 Showing data table instead:")
                st.dataframe(df, use_container_width=True)
        else:
            st.info("📭 No data to visualize")
    
    def _render_data_tab(self, result: Dict[str, Any]):
        """Render data exploration tab"""
        st.subheader("🔍 Data Explorer")
        
        df = result.get('execution_result')
        if df is not None and not df.empty:
            # Data summary
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Rows", len(df))
            with col2:
                st.metric("Columns", len(df.columns))
            with col3:
                memory_usage = df.memory_usage(deep=True).sum() / 1024
                st.metric("Memory", f"{memory_usage:.1f} KB")
            
            # Column selection and filtering
            with st.expander("🔧 Data Controls"):
                # Column selection
                all_columns = df.columns.tolist()
                selected_columns = st.multiselect(
                    "Select columns to display:",
                    all_columns,
                    default=all_columns[:10] if len(all_columns) > 10 else all_columns
                )
                
                # Basic filtering
                if selected_columns:
                    filter_column = st.selectbox("Filter by column:", ["None"] + selected_columns)
                    
                    if filter_column != "None":
                        if df[filter_column].dtype == 'object':
                            unique_values = df[filter_column].unique()[:20]  # Limit for performance
                            selected_values = st.multiselect(f"Select {filter_column} values:", unique_values)
                            if selected_values:
                                df = df[df[filter_column].isin(selected_values)]
                        else:
                            min_val, max_val = float(df[filter_column].min()), float(df[filter_column].max())
                            if min_val != max_val:
                                range_vals = st.slider(f"Select {filter_column} range:", min_val, max_val, (min_val, max_val))
                                df = df[(df[filter_column] >= range_vals[0]) & (df[filter_column] <= range_vals[1])]
            
            # Display data
            if selected_columns:
                display_df = df[selected_columns] if selected_columns else df
                st.dataframe(display_df, use_container_width=True, height=400)
                
                # Download option
                csv = display_df.to_csv(index=False)
                st.download_button(
                    label="📥 Download as CSV",
                    data=csv,
                    file_name=f"query_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv"
                )
            else:
                st.warning("Please select at least one column to display")
        else:
            st.info("📭 No data to display")
    
    def _render_sql_tab(self, result: Dict[str, Any]):
        """Render SQL tab with enhanced information"""
        st.subheader("💻 Generated SQL Query")
        
        sql_query = result.get('generated_sql', '')
        if sql_query:
            # Query info and intent
            col1, col2 = st.columns([2, 1])
            with col1:
                confidence = result.get('confidence_score', 0)
                confidence_color = "🟢" if confidence > 0.7 else "🟡" if confidence > 0.4 else "🔴"
                st.write(f"**Confidence:** {confidence_color} {confidence:.2f}")
                
                # Show query intent if available
                query_intent = result.get('query_intent', {})
                if query_intent.get('type'):
                    st.write(f"**Query Type:** {query_intent['type']}")
            
            with col2:
                if st.button("📋 Copy SQL", use_container_width=True):
                    st.code(sql_query, language='sql')
            
            # SQL display
            st.code(sql_query, language='sql')
            
            # Enhanced query analysis
            with st.expander("🔍 Query Analysis", expanded=True):
                st.write(f"**Original Question:** {result.get('user_query', '')}")
                
                # Show query intent details
                if query_intent:
                    if query_intent.get('entities'):
                        st.write(f"**Tables Used:** {', '.join(query_intent['entities'])}")
                    if query_intent.get('attributes'):
                        st.write(f"**Columns Selected:** {', '.join(query_intent['attributes'])}")
                    if query_intent.get('conditions'):
                        st.write(f"**Conditions Applied:** {', '.join(query_intent['conditions'])}")
                
                # Show execution stats
                exec_stats = result.get('execution_stats', {})
                if exec_stats:
                    col1, col2 = st.columns(2)
                    with col1:
                        st.metric("Rows Returned", exec_stats.get('rows_returned', 0))
                    with col2:
                        exec_time = exec_stats.get('execution_time', 0)
                        st.metric("Execution Time", f"{exec_time:.2f}s")
                
                # Show relevant schema elements
                relevant_schema = result.get('relevant_schema', [])
                if relevant_schema:
                    st.write("**Schema Elements Used:**")
                    for item in relevant_schema[:5]:
                        if isinstance(item, dict):
                            table = item.get('table', 'unknown')
                            columns = item.get('key_columns', [])
                            st.write(f"📋 **{table}**: {', '.join(columns[:5])}")
        else:
            st.info("💻 No SQL query generated")
    
    def _render_insights_tab(self, result: Dict[str, Any]):
        """Render insights tab"""
        st.subheader("🧠 AI-Generated Insights")
        
        df = result.get('execution_result')
        user_query = result.get('user_query', '')
        sql_query = result.get('generated_sql', '')
        
        if df is not None and not df.empty:
            with st.spinner("🤖 Generating insights..."):
                try:
                    insights = chart_generator.generate_insights(df, user_query, sql_query)
                    
                    # Display insights in a nice format
                    st.markdown(f"""
                    <div style="background-color: #f0f8ff; padding: 20px; border-radius: 10px; border-left: 4px solid #4CAF50;">
                        {insights}
                    </div>
                    """, unsafe_allow_html=True)
                    
                except Exception as e:
                    st.error(f"❌ Failed to generate insights: {str(e)}")
            
            # Statistical summary
            with st.expander("📊 Statistical Summary"):
                # Numeric columns
                numeric_cols = df.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0:
                    st.write("**Numeric Columns:**")
                    st.dataframe(df[numeric_cols].describe())
                
                # Categorical columns
                categorical_cols = df.select_dtypes(include=['object']).columns
                if len(categorical_cols) > 0:
                    st.write("**Categorical Columns:**")
                    for col in categorical_cols[:3]:
                        st.write(f"**{col}:** {df[col].nunique()} unique values")
                        if df[col].nunique() <= 10:
                            value_counts = df[col].value_counts()
                            st.write(value_counts)
        else:
            st.info("🤖 No data available for insights generation")
    
    def _render_key_metrics(self, df: pd.DataFrame):
        """Render key metrics from data"""
        if df.empty:
            return
        
        st.subheader("📈 Key Metrics")
        cols = st.columns(4)
        
        with cols[0]:
            st.metric("Total Rows", f"{len(df):,}")
        
        with cols[1]:
            st.metric("Columns", len(df.columns))
        
        # Try to find numeric columns for additional metrics
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            first_numeric = df[numeric_cols[0]]
            
            with cols[2]:
                avg_val = first_numeric.mean()
                st.metric(f"Avg {numeric_cols[0]}", f"{avg_val:,.2f}")
            
            with cols[3]:
                max_val = first_numeric.max()
                st.metric(f"Max {numeric_cols[0]}", f"{max_val:,.2f}")
    
    def _execute_query(self, user_query: str, options: Dict[str, Any]):
        """Execute natural language query"""
        try:
            with st.spinner("🧠 Processing your query..."):
                # Process query through SQL agent
                result = sql_agent.process_query(user_query)
                
                # Add to history
                if 'query_history' not in st.session_state:
                    st.session_state.query_history = []
                
                st.session_state.query_history.append({
                    'query': user_query,
                    'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'result': result
                })
                
                # Store current result
                st.session_state.current_result = result
                
                # Show execution status
                if result.get('error_message'):
                    st.error(f"❌ Error: {result['error_message']}")
                else:
                    execution_result = result.get('execution_result')
                    if execution_result is not None and not execution_result.empty:
                        st.success(f"✅ Query executed successfully! Retrieved {len(execution_result)} rows.")
                    else:
                        st.warning("⚠️ Query executed but returned no data.")
                
                st.rerun()
                
        except Exception as e:
            st.error(f"❌ Execution failed: {str(e)}")
            logger.error(f"Query execution failed: {str(e)}")
    
    def _show_query_suggestions(self):
        """Show intelligent query suggestions based on schema"""
        schema_info = st.session_state.get('schema_info', {})
        
        if schema_info:
            # Get intelligent suggestions from the enterprise agent
            suggestions = sql_agent.get_query_suggestions(schema_info)
            
            if suggestions:
                st.info("💡 **Intelligent Query Suggestions:**\n" + "\n".join([f"• {s}" for s in suggestions]))
            else:
                # Fallback suggestions
                st.info("💡 **Try asking questions like:**\n" + 
                       "• Show me all customers\n" + 
                       "• What are the top 10 products by sales?\n" + 
                       "• Find orders from last month\n" + 
                       "• Compare revenue across regions")
        else:
            st.info("💡 **Try asking questions like:**\n" + 
                   "• Show me all data from [table_name]\n" + 
                   "• What are the top 10 records by [column_name]?\n" + 
                   "• Find records where [condition]")
    
    def _show_query_history(self):
        """Show query history in sidebar or modal"""
        history = st.session_state.get('query_history', [])
        
        if history:
            st.subheader("📊 Query History")
            for i, query_item in enumerate(reversed(history[-10:])):
                with st.expander(f"Query {len(history) - i}: {query_item['query'][:50]}..."):
                    st.write(f"**Time:** {query_item['timestamp']}")
                    st.write(f"**Query:** {query_item['query']}")
                    if st.button(f"🔄 Rerun", key=f"rerun_history_{i}"):
                        st.session_state.main_query_input = query_item['query']
                        st.rerun()
        else:
            st.info("📭 No query history yet")
    
    def _reset_to_wizard(self):
        """Reset to wizard mode"""
        # Clear all session state related to connection and setup
        keys_to_clear = [
            'connected', 'schema_loaded', 'semantic_layer_built', 
            'wizard_step', 'wizard_completed', 'show_query_interface',
            'connection_details', 'schema_info', 'semantic_method'
        ]
        
        for key in keys_to_clear:
            if key in st.session_state:
                del st.session_state[key]
        
        st.rerun()

# Global instance
query_interface = QueryInterface()
