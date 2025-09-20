# 🚀 GenBI - Enterprise Natural Language Business Intelligence

A sophisticated, enterprise-grade Business Intelligence application that converts natural language queries into SQL, executes them against your database, and generates interactive visualizations with AI-powered insights. Now featuring comprehensive authentication and authorization for enterprise security.

---

## 📊 **Key Features**

### **🤖 AI-Powered Query Generation**
- **Natural Language to SQL**: Convert plain English questions into optimized SQL queries
- **Advanced Query Intent Understanding**: AI understands WHAT you want before generating SQL
- **Few-Shot Learning**: Built-in library of common business query patterns
- **Enterprise-Grade Validation**: Multi-layer validation with confidence scoring

### **🔐 Enterprise Security**
- **JWT-based Authentication**: Secure, stateless user sessions
- **Role-Based Access Control (RBAC)**: Fine-grained permissions at database/table/column level
- **Query-Level Authorization**: Every SQL query validated against user permissions
- **Admin Interface**: Complete user management and permission configuration

### **🗄️ Multi-Database Support**
- **PostgreSQL, MySQL, Oracle**: Native support for major databases
- **DynamoDB & Athena**: NoSQL and cloud analytics support
- **Semantic Layer**: Vector-based schema understanding for better query generation
- **Connection Pooling**: Optimized for high-performance enterprise environments

### **📈 Advanced Analytics**
- **Interactive Dashboards**: Automatic chart generation with multiple visualization types
- **AI Insights**: Natural language explanations of your data patterns
- **Query History**: Track and rerun previous queries with user context
- **Real-time Processing**: Powered by LangChain, LangGraph, and modern AI models

---

## 🏗️ **System Architecture**

```
┌─────────────────────────────────────────────────────────────┐
│                    GenBI Application                        │
├─────────────────────────────────────────────────────────────┤
│  Frontend (Streamlit)                                       │
│  ├── Login Interface & Authentication                       │
│  ├── Query Interface (with authorization)                   │
│  └── Admin Panel (role-based access)                       │
├─────────────────────────────────────────────────────────────┤
│  Authentication & Authorization Layer                       │
│  ├── JWT Manager (token handling)                          │
│  ├── User Manager (user data & auth)                       │
│  ├── Authorization Manager (permission checks)             │
│  └── Auth Middleware (integration layer)                   │
├─────────────────────────────────────────────────────────────┤
│  AI & Business Logic Layer                                  │
│  ├── Enterprise SQL Agent (with auth integration)          │
│  ├── Advanced Query Planner (intent understanding)         │
│  ├── Semantic Layer (vector embeddings)                    │
│  └── Query Processing Pipeline                             │
├─────────────────────────────────────────────────────────────┤
│  Data & Visualization Layer                                 │
│  ├── Multi-Database Connectors                             │
│  ├── Vector Database (ChromaDB)                            │
│  ├── Chart Generator (Plotly)                              │
│  └── User Data Store                                       │
└─────────────────────────────────────────────────────────────┘
```

---

## 📋 **Prerequisites**

- **Python 3.8+**
- **AI Provider**: Groq API Key or OpenAI API Key
- **Database Access**: PostgreSQL/MySQL/Oracle/DynamoDB/Athena
- **System Requirements**: 4GB+ RAM (for vector embeddings)

---

## 🛠️ **Installation & Setup**

### **1. Clone and Install**
```bash
git clone <repository-url>
cd genbi
pip install -r requirements.txt
```

### **2. Environment Configuration**
```bash
cp .env.example .env
# Edit .env with your credentials
```

**Required Environment Variables:**
```env
# AI Provider (choose one)
AI_PROVIDER=groq  # or "openai"
GROQ_API_KEY=your_groq_api_key_here
OPENAI_API_KEY=your_openai_api_key_here

# Database Configuration
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=your_database
POSTGRES_USER=your_username
POSTGRES_PASSWORD=your_password

# Vector Database
CHROMA_PERSIST_DIRECTORY=./chroma_db
```

### **3. Start Application**
```bash
# Using the launcher (recommended)
python run.py

# Or directly with Streamlit
streamlit run app.py
```

---

## 🔐 **Authentication & Security**

### **Default Admin Access**
- **Username**: `admin`
- **Password**: `admin123`
- **Permissions**: Full access to all databases, tables, and columns

### **First Login Process**
1. Start the application
2. Login with admin credentials
3. Use the admin panel to create additional users
4. Configure permissions as needed

### **Permission Model**
```json
{
  "databases": ["sales_db", "analytics_db", "*"],
  "tables": ["customers", "orders", "products", "*"],
  "columns": ["customer_name", "order_date", "total_amount", "*"]
}
```

### **Security Features**
- **Query-Level Authorization**: Every SQL query validated before execution
- **Fine-Grained Permissions**: Database → Table → Column level control
- **Audit Trail**: Complete access logging for compliance
- **Secure Sessions**: JWT-based authentication with configurable expiry

---

## 🎯 **Usage Examples**

### **Business Analytics Queries**
```
"Show me the top 10 customers by revenue this year"
→ Generates: Proper JOINs, SUM aggregation, date filtering, ORDER BY, LIMIT

"Compare sales performance across different regions"
→ Generates: GROUP BY region, SUM calculations, proper ordering

"What's the monthly revenue trend for the last 12 months?"
→ Generates: DATE_TRUNC, time filtering, proper time series analysis
```

### **Complex Filtering Queries**
```
"Find customers who haven't ordered in the last 6 months"
→ Generates: LEFT JOIN with NULL checks, date filtering

"Show products with declining sales compared to last quarter"
→ Generates: Subqueries, date comparisons, trend analysis
```

### **Advanced Analytics**
```
"What's the customer lifetime value by segment?"
→ Generates: Complex aggregations, customer segmentation, CLV calculations

"Show seasonal patterns in product sales"
→ Generates: Date functions, seasonal grouping, pattern analysis
```

---

## 👥 **User Management**

### **Creating Users (Admin Only)**
1. Login as admin
2. Click "👥 Manage Users" in sidebar
3. Fill out the create user form:
   - Username and password
   - Assign roles (Admin/Analyst)
   - Set database permissions
   - Set table permissions
   - Set column permissions
4. Click "Create User"

### **User Roles**
- **Admin**: Full system access, user management, permission configuration
- **Analyst**: Query execution based on assigned permissions, data visualization

### **Permission Examples**

**Sales Analyst:**
```json
{
  "databases": ["sales_db"],
  "tables": ["customers", "orders", "products"],
  "columns": ["customer_name", "order_date", "total_amount", "product_name"]
}
```

**Executive Dashboard:**
```json
{
  "databases": ["*"],
  "tables": ["summary_reports", "kpi_dashboard"],
  "columns": ["*"]
}
```

---

## 🚀 **Advanced Features**

### **Enterprise SQL Generation**
- **Intent Analysis**: AI understands query intent before SQL generation
- **Query Classification**: Automatic identification of query types (TOP_N, AGGREGATION, TREND)
- **Relationship Mapping**: Understands table joins and foreign key relationships
- **Performance Optimization**: Automatic query optimization and safety limits

### **Semantic Layer**
- **Vector Embeddings**: Schema elements stored as embeddings for intelligent search
- **Context-Aware**: Finds relevant tables and columns based on natural language
- **Relationship Understanding**: Automatically includes related tables in queries
- **Performance Optimized**: Efficient similarity search for large schemas

### **Visualization Engine**
- **Smart Chart Selection**: Automatic chart type recommendation based on data
- **Interactive Dashboards**: Multiple coordinated views with drill-down capabilities
- **AI Insights**: Natural language explanations of data patterns and trends
- **Export Options**: Download results as CSV or images

---

## 📊 **Supported Query Types**

### **Sales & Revenue Analysis**
- Total sales by time period
- Top customers/products by revenue
- Sales performance comparisons
- Revenue trend analysis

### **Customer Analytics**
- Customer segmentation analysis
- Customer lifetime value calculations
- Churn analysis and retention metrics
- Purchase behavior patterns

### **Product Performance**
- Product profitability analysis
- Inventory level monitoring
- Seasonal sales patterns
- Product category comparisons

### **Operational Metrics**
- Order volume and processing times
- Regional performance analysis
- Delivery and shipping metrics
- Operational efficiency indicators

---

## 🔧 **Configuration**

### **AI Provider Settings**
```env
# Groq Configuration
GROQ_API_KEY=your_groq_api_key
GROQ_MODEL=llama-3.1-70b-versatile

# OpenAI Configuration
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

### **Database Settings**
```env
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
```

### **Performance Tuning**
```env
# Query limits and optimization
MAX_QUERY_RESULTS=10000
CHROMA_PERSIST_DIRECTORY=./chroma_db
EMBEDDING_MODEL=all-MiniLM-L6-v2

# Authentication settings
JWT_EXPIRY_HOURS=24
```

---

## 🧪 **Testing & Validation**

### **Authentication Testing**
1. **Valid Login**: Correct credentials → successful authentication
2. **Invalid Login**: Wrong credentials → authentication failure
3. **Token Expiry**: Expired token → re-authentication required
4. **Permission Validation**: Unauthorized queries → clear error messages

### **Query Testing**
1. **Authorized Queries**: User has permissions → query executes successfully
2. **Unauthorized Access**: No permissions → "Access denied" with specific reason
3. **Complex Queries**: Multi-table joins → proper authorization validation
4. **Error Handling**: Invalid queries → helpful error messages

---

## 🚨 **Troubleshooting**

### **Common Issues**

**Authentication Problems:**
- Check username/password accuracy
- Verify `auth/users.json` exists and is readable
- Ensure PyJWT is installed: `pip install PyJWT`

**Database Connection Issues:**
- Verify database credentials in `.env`
- Check network connectivity to database
- Ensure database is running and accessible

**Permission Errors:**
- Verify user permissions in admin panel
- Check table/column names match exactly
- Ensure wildcard permissions (`*`) if needed

**Performance Issues:**
- Reduce query result limits
- Optimize database indexes
- Check vector database size and performance

### **Debug Mode**
```bash
# Enable detailed logging
export LOG_LEVEL=DEBUG
streamlit run app.py
```

---

## 🔒 **Security Best Practices**

### **Production Deployment**
1. **Change Default Passwords**: Update admin password immediately
2. **Use Strong JWT Secrets**: Set custom JWT_SECRET_KEY in production
3. **Enable HTTPS**: Use SSL/TLS for all communications
4. **Regular Updates**: Keep dependencies updated for security patches

### **User Management**
1. **Principle of Least Privilege**: Grant minimum necessary permissions
2. **Regular Access Reviews**: Periodically review and update user permissions
3. **Strong Password Policies**: Implement password complexity requirements
4. **Audit Logging**: Monitor all access attempts and query executions

---

## 🚀 **Future Enhancements**

### **Short-Term (3-6 months)**
- Multi-Factor Authentication (MFA)
- Advanced password security policies
- Comprehensive audit logging dashboard
- Enhanced admin interface with bulk operations

### **Medium-Term (6-12 months)**
- Single Sign-On (SSO) integration
- External identity provider support (Okta, Azure AD)
- Row-level security implementation
- API key management for programmatic access

### **Long-Term (12+ months)**
- Zero-trust security architecture
- AI-powered security analytics
- Advanced threat detection
- Cloud-native microservices architecture

---

## 📞 **Support & Documentation**

### **Getting Help**
1. Check this README for common issues
2. Review application logs for error details
3. Verify configuration settings
4. Contact system administrator for permission issues

### **Contributing**
1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

---

## 📄 **License**

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🙏 **Acknowledgments**

- **LangChain & LangGraph**: AI framework and workflow orchestration
- **Groq & OpenAI**: Fast LLM inference and AI capabilities
- **Streamlit**: Web interface framework
- **ChromaDB**: Vector database for semantic search
- **Plotly**: Interactive visualization library
- **SQLAlchemy**: Database abstraction layer

---

**GenBI** - Making enterprise data accessible through natural language with enterprise-grade security! 🚀📊🔐

---

*For detailed technical documentation, security specifications, and implementation details, refer to the comprehensive documentation included with this project.*
