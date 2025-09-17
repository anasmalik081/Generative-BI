# GenBI - Natural Language Business Intelligence

A sophisticated Business Intelligence application that converts natural language queries into SQL, executes them against your database, and generates interactive visualizations with AI-powered insights.

## 🚀 Features

- **Natural Language to SQL**: Convert plain English questions into optimized SQL queries
- **Multi-Database Support**: Connect to PostgreSQL, MySQL, and Oracle databases
- **Semantic Layer**: Vector-based schema understanding for better query generation
- **Interactive Dashboards**: Automatic chart generation with multiple visualization types
- **AI Insights**: Natural language explanations of your data patterns
- **Query History**: Track and rerun previous queries
- **Real-time Processing**: Powered by LangChain, LangGraph, and Groq models
- **Scalable Architecture**: Optimized for databases with millions of records

## 🏗️ Architecture

```
GenBI Application
├── Frontend (Streamlit)
├── AI Agents (LangChain + LangGraph)
├── Semantic Layer (ChromaDB + Vector Embeddings)
├── Database Connectors (SQLAlchemy)
└── Visualization Engine (Plotly)
```

## 📋 Prerequisites

- Python 3.8+
- Groq API Key
- Database access (PostgreSQL/MySQL/Oracle)
- 4GB+ RAM (for vector embeddings)

## 🛠️ Installation

1. **Clone and navigate to the project:**
```bash
cd genbi_app
```

2. **Install dependencies:**
```bash
pip install -r requirements.txt
```

3. **Configure environment:**
```bash
cp .env.example .env
# Edit .env with your credentials
```

4. **Set up your environment variables:**
```env
# Groq API Configuration
GROQ_API_KEY=your_groq_api_key_here

# Database Configuration (choose one)
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=your_database
POSTGRES_USER=your_username
POSTGRES_PASSWORD=your_password
```

## 🚀 Quick Start

1. **Start the application:**
```bash
streamlit run app.py
```

2. **Connect to your database:**
   - Use the sidebar to select database type
   - Enter connection details
   - Click "Connect"

3. **Ask questions in natural language:**
   - "Show me top 10 customers by revenue"
   - "What's the monthly sales trend?"
   - "Find products with declining sales"

## 📊 Supported Query Types

### Sales & Revenue Analysis
- "Show me total sales by month for the last year"
- "What are the top 5 products by revenue?"
- "Compare sales performance across regions"

### Customer Analytics
- "Find customers who haven't purchased in 6 months"
- "Show customer lifetime value distribution"
- "What's the average order value by customer segment?"

### Product Performance
- "Which products have the highest profit margins?"
- "Show inventory levels for low-stock items"
- "Find products with seasonal sales patterns"

### Operational Metrics
- "Show daily order volumes for the last quarter"
- "What's the average delivery time by region?"
- "Find orders with shipping delays"

## 🎯 Key Components

### 1. SQL Agent (`agents/sql_agent.py`)
- **LangGraph Workflow**: Multi-step SQL generation process
- **Schema-Aware**: Uses semantic layer for context
- **Error Handling**: Automatic query refinement
- **Validation**: SQL syntax and security checks

### 2. Semantic Layer (`semantic_layer/vector_store.py`)
- **Vector Embeddings**: Schema elements stored as embeddings
- **Similarity Search**: Find relevant tables/columns
- **Business Glossary**: Custom term definitions
- **Performance**: Optimized for large schemas (1000+ columns)

### 3. Database Manager (`database/connection_manager.py`)
- **Multi-DB Support**: PostgreSQL, MySQL, Oracle
- **Connection Pooling**: Efficient resource management
- **Schema Introspection**: Automatic metadata extraction
- **Query Optimization**: Built-in performance safeguards

### 4. Visualization Engine (`visualization/chart_generator.py`)
- **Smart Chart Selection**: Automatic chart type recommendation
- **Interactive Dashboards**: Multiple coordinated views
- **AI Insights**: Natural language data explanations
- **Export Options**: Download results as CSV

## 🔧 Configuration

### Database Settings
```python
# PostgreSQL
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=your_database
POSTGRES_USER=your_username
POSTGRES_PASSWORD=your_password

# MySQL
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_DB=your_database
MYSQL_USER=your_username
MYSQL_PASSWORD=your_password

# Oracle
ORACLE_HOST=localhost
ORACLE_PORT=1521
ORACLE_SERVICE=your_service
ORACLE_USER=your_username
ORACLE_PASSWORD=your_password
```

### Performance Tuning
```python
# Maximum query results (safety limit)
MAX_QUERY_RESULTS=10000

# Vector database settings
CHROMA_PERSIST_DIRECTORY=./chroma_db

# Model settings
EMBEDDING_MODEL=all-MiniLM-L6-v2
CHAT_MODEL=mixtral-8x7b-32768
```

## 📈 Performance Optimization

### For Large Databases (Millions of Records)

1. **Semantic Layer Optimization:**
   - Schema embeddings are created once and cached
   - Vector similarity search reduces query scope
   - Intelligent column selection for complex schemas

2. **Query Optimization:**
   - Automatic LIMIT clauses for safety
   - Connection pooling for concurrent users
   - Query result caching (can be implemented)

3. **Memory Management:**
   - Streaming results for large datasets
   - Efficient DataFrame operations
   - Vector database persistence

## 🔒 Security Features

- **SQL Injection Prevention**: Query validation and sanitization
- **Connection Security**: Encrypted database connections
- **Access Control**: Environment-based configuration
- **Query Limits**: Automatic result size restrictions

## 🧪 Example Queries

### Business Questions → Generated SQL

**Question:** "Show me the top 5 customers by total revenue this year"
```sql
SELECT 
    c.customer_name,
    SUM(o.total_amount) as total_revenue
FROM customers c
JOIN orders o ON c.customer_id = o.customer_id
WHERE EXTRACT(YEAR FROM o.order_date) = EXTRACT(YEAR FROM CURRENT_DATE)
GROUP BY c.customer_id, c.customer_name
ORDER BY total_revenue DESC
LIMIT 5;
```

**Question:** "What's the monthly sales trend for the last 6 months?"
```sql
SELECT 
    DATE_TRUNC('month', order_date) as month,
    SUM(total_amount) as monthly_sales
FROM orders
WHERE order_date >= CURRENT_DATE - INTERVAL '6 months'
GROUP BY DATE_TRUNC('month', order_date)
ORDER BY month;
```

## 🎨 Visualization Types

- **Bar Charts**: Category comparisons
- **Line Charts**: Time series trends
- **Scatter Plots**: Correlation analysis
- **Pie Charts**: Distribution analysis
- **Heatmaps**: Correlation matrices
- **Box Plots**: Statistical distributions
- **Interactive Tables**: Detailed data exploration

## 🔍 Troubleshooting

### Common Issues

1. **Connection Failed:**
   - Check database credentials
   - Verify network connectivity
   - Ensure database is running

2. **Query Generation Errors:**
   - Verify Groq API key
   - Check schema loading status
   - Review query complexity

3. **Performance Issues:**
   - Reduce query result limits
   - Optimize database indexes
   - Check vector database size

### Debug Mode
```bash
# Enable detailed logging
export LOG_LEVEL=DEBUG
streamlit run app.py
```

## 🚀 Deployment

### Local Development
```bash
streamlit run app.py --server.port 8501
```

### Production Deployment
```bash
# Using Docker (create Dockerfile)
docker build -t genbi-app .
docker run -p 8501:8501 genbi-app

# Using cloud platforms
# Deploy to Streamlit Cloud, AWS, GCP, or Azure
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **LangChain**: For the AI framework
- **LangGraph**: For workflow orchestration
- **Groq**: For fast LLM inference
- **Streamlit**: For the web interface
- **ChromaDB**: For vector storage
- **Plotly**: For interactive visualizations

## 📞 Support

For support and questions:
- Create an issue in the repository
- Check the troubleshooting section
- Review the example queries

---

**GenBI** - Making data accessible through natural language! 🚀📊
