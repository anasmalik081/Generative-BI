import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict, List, Any, Optional, Tuple
import numpy as np
from config.llm_factory import llm_factory
from langchain.prompts import ChatPromptTemplate
from config.settings import settings
import logging

logger = logging.getLogger(__name__)

class ChartGenerator:
    def __init__(self):
        self.llm = llm_factory.get_chat_model()
    
    def analyze_data_for_visualization(self, df: pd.DataFrame, user_query: str) -> Dict[str, Any]:
        """Analyze data to determine the best visualization approach"""
        if df.empty:
            return {"chart_type": "none", "message": "No data to visualize"}
        
        analysis = {
            "row_count": len(df),
            "column_count": len(df.columns),
            "numeric_columns": [],
            "categorical_columns": [],
            "datetime_columns": [],
            "recommended_charts": []
        }
        
        # Analyze column types
        for col in df.columns:
            if pd.api.types.is_numeric_dtype(df[col]):
                analysis["numeric_columns"].append(col)
            elif pd.api.types.is_datetime64_any_dtype(df[col]):
                analysis["datetime_columns"].append(col)
            else:
                analysis["categorical_columns"].append(col)
        
        # Recommend chart types based on data structure
        analysis["recommended_charts"] = self._recommend_chart_types(analysis, user_query)
        
        return analysis
    
    def _recommend_chart_types(self, analysis: Dict, user_query: str) -> List[str]:
        """Recommend appropriate chart types based on data analysis"""
        recommendations = []
        
        numeric_count = len(analysis["numeric_columns"])
        categorical_count = len(analysis["categorical_columns"])
        datetime_count = len(analysis["datetime_columns"])
        
        # Time series data
        if datetime_count > 0 and numeric_count > 0:
            recommendations.extend(["line", "area"])
        
        # Single numeric column
        if numeric_count == 1:
            if categorical_count > 0:
                recommendations.extend(["bar", "pie"])
            else:
                recommendations.append("histogram")
        
        # Two numeric columns
        if numeric_count == 2:
            recommendations.append("scatter")
        
        # Multiple numeric columns
        if numeric_count > 2:
            recommendations.extend(["correlation_heatmap", "box"])
        
        # Categorical data
        if categorical_count > 0 and numeric_count > 0:
            recommendations.extend(["bar", "pie"])
        
        # Default fallback
        if not recommendations:
            recommendations.append("table")
        
        return recommendations
    
    def create_chart(self, df: pd.DataFrame, chart_type: str, **kwargs) -> go.Figure:
        """Create interactive chart based on type and data"""
        try:
            if df.empty:
                return self._create_empty_chart("No data available")
            
            chart_methods = {
                "bar": self._create_bar_chart,
                "line": self._create_line_chart,
                "scatter": self._create_scatter_chart,
                "pie": self._create_pie_chart,
                "histogram": self._create_histogram,
                "box": self._create_box_plot,
                "heatmap": self._create_heatmap,
                "correlation_heatmap": self._create_correlation_heatmap,
                "area": self._create_area_chart,
                "table": self._create_table_chart
            }
            
            if chart_type in chart_methods:
                return chart_methods[chart_type](df, **kwargs)
            else:
                return self._create_bar_chart(df, **kwargs)
                
        except Exception as e:
            logger.error(f"Chart creation failed: {str(e)}")
            return self._create_empty_chart(f"Chart creation failed: {str(e)}")
    
    def _create_bar_chart(self, df: pd.DataFrame, **kwargs) -> go.Figure:
        """Create bar chart"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()
        
        if not numeric_cols or not categorical_cols:
            # Fallback: use first two columns
            x_col = df.columns[0] if len(df.columns) > 0 else None
            y_col = df.columns[1] if len(df.columns) > 1 else df.columns[0]
        else:
            x_col = categorical_cols[0]
            y_col = numeric_cols[0]
        
        if x_col and y_col:
            # Group by x_col and sum y_col if needed
            try:
                if df[x_col].nunique() < len(df):
                    grouped_df = df.groupby(x_col)[y_col].sum().reset_index()
                    fig = px.bar(grouped_df, x=x_col, y=y_col, title=f"{y_col} by {x_col}")
                else:
                    fig = px.bar(df, x=x_col, y=y_col, title=f"{y_col} by {x_col}")
            except Exception as e:
                # Fallback to simple bar chart
                fig = px.bar(df, x=x_col, y=y_col, title=f"{y_col} by {x_col}")
        else:
            fig = px.bar(df.head(20), title="Data Overview")
        
        fig.update_layout(height=500, showlegend=True)
        return fig
    
    def _create_line_chart(self, df: pd.DataFrame, **kwargs) -> go.Figure:
        """Create line chart"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        datetime_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
        
        if datetime_cols and numeric_cols:
            x_col = datetime_cols[0]
            y_col = numeric_cols[0]
            fig = px.line(df, x=x_col, y=y_col, title=f"{y_col} over {x_col}")
        elif len(df.columns) >= 2:
            fig = px.line(df, x=df.columns[0], y=df.columns[1], title="Trend Analysis")
        else:
            fig = px.line(df, y=df.columns[0], title="Data Trend")
        
        fig.update_layout(height=500)
        return fig
    
    def _create_scatter_chart(self, df: pd.DataFrame, **kwargs) -> go.Figure:
        """Create scatter plot"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if len(numeric_cols) >= 2:
            x_col = numeric_cols[0]
            y_col = numeric_cols[1]
            
            # Add color dimension if available
            color_col = None
            categorical_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()
            if categorical_cols:
                color_col = categorical_cols[0]
            
            fig = px.scatter(df, x=x_col, y=y_col, color=color_col, 
                           title=f"{y_col} vs {x_col}")
        else:
            fig = px.scatter(df, title="Scatter Plot")
        
        fig.update_layout(height=500)
        return fig
    
    def _create_pie_chart(self, df: pd.DataFrame, **kwargs) -> go.Figure:
        """Create pie chart"""
        categorical_cols = df.select_dtypes(exclude=[np.number]).columns.tolist()
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if categorical_cols and numeric_cols:
            category_col = categorical_cols[0]
            value_col = numeric_cols[0]
            
            # Group and sum values
            grouped_df = df.groupby(category_col)[value_col].sum().reset_index()
            fig = px.pie(grouped_df, values=value_col, names=category_col, 
                        title=f"Distribution of {value_col} by {category_col}")
        elif categorical_cols:
            # Count occurrences
            value_counts = df[categorical_cols[0]].value_counts()
            fig = px.pie(values=value_counts.values, names=value_counts.index,
                        title=f"Distribution of {categorical_cols[0]}")
        else:
            fig = px.pie(title="No categorical data for pie chart")
        
        fig.update_layout(height=500)
        return fig
    
    def _create_histogram(self, df: pd.DataFrame, **kwargs) -> go.Figure:
        """Create histogram"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if numeric_cols:
            col = numeric_cols[0]
            fig = px.histogram(df, x=col, title=f"Distribution of {col}")
        else:
            fig = px.histogram(df, title="Histogram")
        
        fig.update_layout(height=500)
        return fig
    
    def _create_box_plot(self, df: pd.DataFrame, **kwargs) -> go.Figure:
        """Create box plot"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        
        if len(numeric_cols) > 1:
            fig = go.Figure()
            for col in numeric_cols[:5]:  # Limit to 5 columns
                fig.add_trace(go.Box(y=df[col], name=col))
            fig.update_layout(title="Box Plot Comparison", height=500)
        elif numeric_cols:
            fig = px.box(df, y=numeric_cols[0], title=f"Box Plot of {numeric_cols[0]}")
        else:
            fig = go.Figure()
            fig.update_layout(title="No numeric data for box plot", height=500)
        
        return fig
    
    def _create_heatmap(self, df: pd.DataFrame, **kwargs) -> go.Figure:
        """Create heatmap"""
        numeric_df = df.select_dtypes(include=[np.number])
        
        if not numeric_df.empty:
            fig = px.imshow(numeric_df.corr(), 
                          title="Correlation Heatmap",
                          color_continuous_scale="RdBu_r")
        else:
            fig = go.Figure()
            fig.update_layout(title="No numeric data for heatmap", height=500)
        
        fig.update_layout(height=500)
        return fig
    
    def _create_correlation_heatmap(self, df: pd.DataFrame, **kwargs) -> go.Figure:
        """Create correlation heatmap"""
        return self._create_heatmap(df, **kwargs)
    
    def _create_area_chart(self, df: pd.DataFrame, **kwargs) -> go.Figure:
        """Create area chart"""
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        datetime_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
        
        if datetime_cols and numeric_cols:
            x_col = datetime_cols[0]
            y_col = numeric_cols[0]
            fig = px.area(df, x=x_col, y=y_col, title=f"{y_col} over {x_col}")
        elif len(df.columns) >= 2:
            fig = px.area(df, x=df.columns[0], y=df.columns[1], title="Area Chart")
        else:
            fig = px.area(df, y=df.columns[0], title="Area Chart")
        
        fig.update_layout(height=500)
        return fig
    
    def _create_table_chart(self, df: pd.DataFrame, **kwargs) -> go.Figure:
        """Create interactive table"""
        fig = go.Figure(data=[go.Table(
            header=dict(values=list(df.columns),
                       fill_color='paleturquoise',
                       align='left'),
            cells=dict(values=[df[col] for col in df.columns],
                      fill_color='lavender',
                      align='left'))
        ])
        
        fig.update_layout(title="Data Table", height=500)
        return fig
    
    def _create_empty_chart(self, message: str) -> go.Figure:
        """Create empty chart with message"""
        fig = go.Figure()
        fig.add_annotation(
            text=message,
            xref="paper", yref="paper",
            x=0.5, y=0.5,
            showarrow=False,
            font=dict(size=16)
        )
        fig.update_layout(
            title="No Data",
            height=400,
            xaxis=dict(showgrid=False, showticklabels=False),
            yaxis=dict(showgrid=False, showticklabels=False)
        )
        return fig
    
    def generate_insights(self, df: pd.DataFrame, user_query: str, sql_query: str) -> str:
        """Generate natural language insights about the data"""
        try:
            if df.empty:
                return "No data was returned from the query."
            
            # Basic statistics
            stats = {
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": list(df.columns)
            }
            
            # Numeric column statistics
            numeric_stats = {}
            for col in df.select_dtypes(include=[np.number]).columns:
                numeric_stats[col] = {
                    "mean": df[col].mean(),
                    "median": df[col].median(),
                    "std": df[col].std(),
                    "min": df[col].min(),
                    "max": df[col].max()
                }
            
            # Create prompt for insights generation
            prompt = ChatPromptTemplate.from_template("""
            Analyze the following data and provide key insights in natural language.
            
            User Query: {user_query}
            SQL Query: {sql_query}
            
            Data Summary:
            - Total rows: {row_count}
            - Columns: {columns}
            
            Numeric Statistics:
            {numeric_stats}
            
            Sample Data (first 5 rows):
            {sample_data}
            
            Please provide:
            1. A summary of what the data shows
            2. Key findings and patterns
            3. Notable statistics or trends
            4. Answers to the original question
            
            Keep the response concise but informative, focusing on actionable insights.
            """)
            
            sample_data = df.head().to_string()
            
            chain = prompt | self.llm
            
            insights = chain.invoke({
                "user_query": user_query,
                "sql_query": sql_query,
                "row_count": stats["row_count"],
                "columns": ", ".join(stats["columns"]),
                "numeric_stats": str(numeric_stats),
                "sample_data": sample_data
            })
            
            return insights.content
            
        except Exception as e:
            logger.error(f"Insights generation failed: {str(e)}")
            return f"Unable to generate insights: {str(e)}"
    
    def create_dashboard(self, df: pd.DataFrame, user_query: str) -> List[go.Figure]:
        """Create multiple charts for a comprehensive dashboard"""
        if df.empty:
            return [self._create_empty_chart("No data available")]
        
        analysis = self.analyze_data_for_visualization(df, user_query)
        charts = []
        
        # Create up to 3 different chart types
        recommended_charts = analysis["recommended_charts"][:3]
        
        for chart_type in recommended_charts:
            try:
                chart = self.create_chart(df, chart_type)
                charts.append(chart)
            except Exception as e:
                logger.error(f"Failed to create {chart_type} chart: {str(e)}")
        
        # Ensure at least one chart
        if not charts:
            charts.append(self._create_table_chart(df))
        
        return charts

# Global instance
chart_generator = ChartGenerator()
