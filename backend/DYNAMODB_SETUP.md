# DynamoDB Integration Setup

This Django project has been configured to connect to your existing DynamoDB tables.

## Quick Setup

1. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure AWS credentials:**
   ```bash
   cp .env.example .env
   # Edit .env with your AWS credentials
   ```

3. **Test the connection:**
   ```bash
   python setup_dynamodb.py
   ```

4. **Run the Django server:**
   ```bash
   python manage.py runserver
   ```

## Environment Variables

Create a `.env` file with:
```
AWS_ACCESS_KEY_ID=your_access_key_here
AWS_SECRET_ACCESS_KEY=your_secret_key_here
AWS_REGION=us-east-2
```

## DynamoDB Tables

The following tables are configured:
- **Users**: User authentication data
- **Groups**: Product/stock groups hierarchy  
- **YourStockTableName**: Stock inventory data
- **YourTransactionsTableName**: Transaction history
- **production**: Production records
- **undo_actions**: Undo operation tracking
- **products**: Product definitions

## API Endpoints

### Users
- `POST /api/users/register/` - Register user
- `POST /api/users/login/` - User login  
- `POST /api/users/admin/view/` - Admin view users
- `POST /api/users/admin/update/` - Admin update user

### Stock & Groups
- `POST /api/stock/groups/create/` - Create group
- `GET /api/stock/groups/list/` - List groups
- `POST /api/stock/create/` - Create stock item
- `GET /api/stock/list/` - List all stocks

## What's Working

✅ **Users app**: Fully connected to DynamoDB
- User registration with password hashing
- User login with authentication
- Admin user management

✅ **Stock app**: Partially connected
- Group creation and listing
- Basic stock operations (create, update, delete)

## Next Steps

1. Complete stock operations implementation
2. Add production workflow integration  
3. Implement reports functionality
4. Add comprehensive error handling
5. Add data validation and sanitization

## Troubleshooting

**Connection Issues:**
- Verify AWS credentials in `.env`
- Check AWS region matches your DynamoDB tables
- Ensure IAM permissions for DynamoDB access

**Table Access Issues:**
- Verify table names in `settings.py` match your DynamoDB tables
- Check IAM permissions for specific table operations