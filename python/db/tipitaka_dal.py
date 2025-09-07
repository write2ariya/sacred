#!/usr/bin/env python3
"""
Tipitaka Database Access Layer (DAL) using pyDAL
Provides models and database connection for Tipitaka Pali database
"""

from pydal import DAL, Field
import os
from datetime import datetime

class TipitakaDAL:
    """
    Data Access Layer for Tipitaka Pali database
    """
    
    def __init__(self, db_path=None, auto_connect=False):
        """
        Initialize the DAL connection
        
        Args:
            db_path (str): Path to the SQLite database file
            auto_connect (bool): Automatically connect on initialization
        """
        if db_path is None:
            # Default to the database in the same directory
            current_dir = os.path.dirname(os.path.abspath(__file__))
            db_path = os.path.join(current_dir, 'tipitaka_pali.db')
        
        self.db_path = db_path
        self.db = None
        
        if auto_connect:
            self.connect()

        
    def connect(self):
        """
        Establish database connection and define models
        """
        try:
            # Connect to existing SQLite database
            self.db = DAL(f'sqlite://{self.db_path}', 
                         check_reserved=False,  # Completely disable reserved keyword checking
                         migrate=False,  # Don't migrate existing database
                         fake_migrate=True)  # Use existing structure
            
            # Define common Tipitaka database models
            self._define_models()
            
            return True
            
        except Exception as e:
            print(f"Database connection error: {e}")
            return False
    
    def _define_models(self):
        """
        Define database models based on actual database structure
        """
        
        # Pages table - Individual pages of text  
        self.db.define_table('pages',
            Field('id', 'integer'),
            Field('bookid', 'text'),
            Field('page', 'integer'),
            Field('content', 'text'),
            Field('paranum', 'text'),
            migrate=False
        )
        
        # Category table
        self.db.define_table('category',
            Field('id', 'string', length=255),
            Field('name', 'text'),
            Field('basket', 'text'),
            primarykey=['id'],
            migrate=False
        )
        
        # Books table - Book information
        self.db.define_table('books',
            Field('id', 'string', length=255),
            Field('basket', 'text'),
            Field('category', 'text'),
            Field('name', 'text'),
            Field('firstpage', 'integer'),
            Field('lastpage', 'integer'),
            Field('pagecount', 'integer'),
            Field('toc', 'text'),
            Field('abbr', 'text'),
            primarykey=['id'],
            migrate=False
        )
        
        # Paragraphs table
        self.db.define_table('paragraphs',
            Field('book_id', 'text'),
            Field('paragraph_number', 'integer'),
            Field('page_number', 'integer'),
            primarykey=['book_id', 'paragraph_number', 'page_number'],
            migrate=False
        )
        
        # Dictionary table
        self.db.define_table('dictionary',
            Field('word', 'text'),
            Field('definition', 'text'),
            Field('book', 'integer'),
            primarykey=['word', 'book'],
            migrate=False
        )
        
        # Pali Attha Tika Match table
        self.db.define_table('pali_attha_tika_match',
            Field('base', 'text'),
            Field('exp', 'text'),
            primarykey=['base', 'exp'],
            migrate=False
        )
        
        # TOCs table
        self.db.define_table('tocs',
            Field('book_id', 'text'),
            Field('name', 'text'),
            Field('type', 'text'),
            Field('page_number', 'integer'),
            primarykey=['book_id', 'name'],
            migrate=False
        )
        
        # Paragraph mapping table
        self.db.define_table('paragraph_mapping',
            Field('paragraph', 'integer'),
            Field('base_book_id', 'text'),
            Field('base_page_number', 'integer'),
            Field('exp_book_id', 'text'),
            Field('exp_page_number', 'integer'),
            primarykey=['paragraph', 'base_book_id', 'base_page_number', 'exp_book_id', 'exp_page_number'],
            migrate=False
        )
        
        # Translation books table
        self.db.define_table('tran_books',
            Field('bookid', 'text'),
            Field('tran_bookid', 'text'),
            primarykey=['bookid', 'tran_bookid'],
            migrate=False
        )

    def close(self):
        """
        Close database connection
        """
        if self.db:
            self.db.close()
    
    def __enter__(self):
        """
        Context manager entry
        """
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Context manager exit
        """
        self.close()

# Convenience function to get a connected DAL instance
def get_tipitaka_dal(db_path=None):
    """
    Get a connected TipitakaDAL instance
    
    Args:
        db_path (str): Path to database file
        
    Returns:
        TipitakaDAL: Connected DAL instance
    """
    dal = TipitakaDAL(db_path)
    if dal.connect():
        return dal
    else:
        raise Exception("Failed to connect to Tipitaka database")

# Example usage
if __name__ == "__main__":
    # Test the DAL
    try:
        with TipitakaDAL() as dal:
            print("Connected to Tipitaka database successfully!")
            
            # Get root books
            books = dal.get_books()
            print(f"\nFound {len(books)} root books:")
            for book in books:
                print(f"  - {book.name} ({book.id})")
            
            # Get first book's pages (limited)
            if books:
                first_book = books[0]
                pages = dal.get_pages_by_book(first_book.id, limit=5)
                print(f"\nFirst 5 pages of '{first_book.name}':")
                for page in pages:
                    print(f"  Page {page.page_number}: {len(page.content or '')} characters")
    
    except Exception as e:
        print(f"Error: {e}")
