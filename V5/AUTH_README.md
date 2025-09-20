# 🔐 GenBI Authentication & Authorization System

## Overview

The GenBI application now includes a comprehensive authentication and authorization system that provides:

- **JWT-based Authentication**: Secure, stateless user sessions
- **Role-Based Access Control (RBAC)**: Fine-grained permissions
- **Query-Level Authorization**: SQL query validation against user permissions
- **Admin Interface**: User management and permission configuration

## 🚀 Quick Start

### Default Admin User
- **Username**: `admin`
- **Password**: `admin123`
- **Permissions**: Full access to all databases, tables, and columns

### First Login
1. Start the application: `streamlit run app.py`
2. Login with admin credentials
3. Use the admin panel to create additional users

## 🏗️ Architecture

### Components

1. **JWT Manager** (`auth/jwt_manager.py`)
   - Token creation and validation
   - Session management
   - User context handling

2. **User Manager** (`auth/user_manager.py`)
   - User creation and authentication
   - Password hashing
   - User data persistence

3. **Authorization Manager** (`auth/authorization_manager.py`)
   - Permission checking
   - SQL query authorization
   - Schema filtering

4. **Auth Middleware** (`auth/auth_middleware.py`)
   - Authentication enforcement
   - Query interception
   - UI integration

5. **Admin Interface** (`auth/admin_interface.py`)
   - User management UI
   - Permission configuration
   - Admin-only features

## 🔑 Permission System

### Permission Levels

1. **Database Level**: Control access to entire databases
2. **Table Level**: Control access to specific tables
3. **Column Level**: Control access to specific columns

### Permission Format

```json
{
  "databases": ["sales_db", "analytics_db", "*"],
  "tables": ["customers", "orders", "products", "*"],
  "columns": ["customer_name", "order_date", "total_amount", "*"]
}
```

- Use `"*"` for wildcard access
- Use `"table.column"` format for specific column access
- Permissions are additive (if user has access to any level, access is granted)

### Example Permissions

**Full Admin Access:**
```json
{
  "databases": ["*"],
  "tables": ["*"],
  "columns": ["*"]
}
```

**Sales Analyst:**
```json
{
  "databases": ["sales_db"],
  "tables": ["customers", "orders", "products"],
  "columns": ["customer_name", "order_date", "total_amount", "product_name"]
}
```

**Limited Viewer:**
```json
{
  "databases": ["public_db"],
  "tables": ["summary_reports"],
  "columns": ["report_date", "total_sales", "region"]
}
```

## 🔒 Security Features

### Authentication
- **JWT Tokens**: Secure, stateless authentication
- **Password Hashing**: SHA-256 hashed passwords
- **Session Management**: Automatic token expiry
- **Logout Functionality**: Secure session termination

### Authorization
- **Query-Level Checks**: Every SQL query is validated
- **Real-Time Validation**: Permissions checked before execution
- **Schema Filtering**: Users only see authorized schema elements
- **Access Denied Messages**: Clear feedback on permission issues

### Security Best Practices
- **No Sensitive Data Exposure**: Permissions filter results
- **SQL Injection Prevention**: Combined with existing SQL validation
- **Audit Trail**: All queries logged with user context
- **Role Separation**: Admin vs regular user roles

## 👥 User Management

### Creating Users (Admin Only)

1. Login as admin
2. Click "👥 Manage Users" in sidebar
3. Fill out the create user form:
   - Username and password
   - Assign roles (Admin/Analyst)
   - Set database permissions
   - Set table permissions
   - Set column permissions
4. Click "Create User"

### User Roles

**Admin Role:**
- Full system access
- User management capabilities
- Permission configuration
- System administration

**Analyst Role:**
- Query execution based on permissions
- Data visualization
- Report generation
- Limited to assigned data

## 🔧 Integration Points

### Existing Components Enhanced

1. **Enterprise SQL Agent**: Now checks authorization before query execution
2. **Semantic Layer**: Unchanged - still builds full embeddings for all users
3. **Query Interface**: Shows user info and handles auth errors
4. **Setup Wizard**: Unchanged functionality
5. **Database Manager**: Unchanged - authorization happens at query level

### New Authentication Flow

```
User Login → JWT Token → Query Request → Authorization Check → SQL Execution
```

### Query Processing with Auth

```
1. User submits natural language query
2. SQL is generated from query
3. Authorization manager validates SQL against user permissions
4. If authorized: Execute query and return results
5. If not authorized: Return "Access Denied" message
```

## 🚨 Error Handling

### Authentication Errors
- **Invalid Credentials**: Clear error message
- **Expired Token**: Automatic redirect to login
- **No Token**: Login form displayed

### Authorization Errors
- **Table Access Denied**: "Access denied to table: table_name"
- **Column Access Denied**: "Access denied to column: column_name"
- **Database Access Denied**: "Access denied to database: db_name"

## 📊 Usage Examples

### Authorized Query
```
User Query: "Show me total sales by month"
Generated SQL: SELECT DATE_TRUNC('month', order_date) as month, SUM(total_amount) FROM orders GROUP BY month
Authorization: ✅ User has access to 'orders' table and 'order_date', 'total_amount' columns
Result: Query executed successfully
```

### Unauthorized Query
```
User Query: "Show me employee salaries"
Generated SQL: SELECT employee_name, salary FROM employees
Authorization: ❌ User does not have access to 'employees' table
Result: "Access denied to table: employees"
```

## 🔄 Migration from Existing System

### No Breaking Changes
- Existing functionality remains intact
- Authentication is additive security layer
- Semantic layer building unchanged
- All existing queries work for authorized users

### Backward Compatibility
- Default admin user provides full access
- Existing database connections unchanged
- All visualization features preserved
- Query history maintained

## 🛠️ Configuration

### Environment Variables
```env
# Optional JWT configuration
JWT_SECRET_KEY=your_secret_key
JWT_EXPIRY_HOURS=24
```

### User Data Storage
- Users stored in `auth/users.json`
- Passwords hashed with SHA-256
- Permissions stored per user
- Automatic backup recommended

## 🔍 Troubleshooting

### Common Issues

1. **Can't Login**
   - Check username/password
   - Verify `auth/users.json` exists
   - Check for typos in credentials

2. **Access Denied Errors**
   - Verify user permissions in admin panel
   - Check table/column names match exactly
   - Ensure wildcard permissions if needed

3. **Admin Panel Not Visible**
   - Ensure user has "admin" role
   - Check JWT token validity
   - Verify admin permissions

### Debug Mode
```python
# Enable detailed auth logging
import logging
logging.getLogger('auth').setLevel(logging.DEBUG)
```

## 🚀 Future Enhancements

### Planned Features
- **LDAP/Active Directory Integration**
- **Multi-Factor Authentication**
- **Audit Log Dashboard**
- **Dynamic Permission Updates**
- **API Key Authentication**
- **Row-Level Security**

### Enterprise Features
- **SAML/OAuth2 Integration**
- **Attribute-Based Access Control**
- **Data Masking**
- **Compliance Reporting**

## 📞 Support

For authentication-related issues:
1. Check this documentation
2. Verify user permissions
3. Review application logs
4. Contact system administrator

---

**Security Note**: Always use strong passwords and regularly rotate JWT secrets in production environments.
