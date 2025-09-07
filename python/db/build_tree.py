import shutil
from pathlib import Path
from tipitaka_dal import TipitakaDAL
from aksharamukha import transliterate


class TipitakaBuilder:
    """
    A systematic builder for generating Tipitaka documentation files across multiple scripts.
    
    This class handles the conversion of Myanmar Tipitaka texts into various scripts
    (Roman IAST, Thai, Sinhala, Devanagari, Khmer, Lao, Lanna) and generates
    structured Markdown files for Astro Starlight documentation.
    """
    
    def __init__(self):
        """Initialize the builder with configuration and database connection."""
        self.dal = None
        self.db = None
        self._setup_configuration()
        self._setup_paths()
        
    def _setup_configuration(self):
        """Configure script codes, transliteration mappings, and directory structure."""
        # Script codes following ISO 15924 standard
        self.script_codes = ['mymr', 'thai', 'sinh', 'romn', 'deva', 'khmr', 'laoo', 'lana']
        
        # Transliteration configuration mapping
        self.transliteration_config = [
            {
                "code": "romn",
                "from": "Burmese",
                "to": "IASTPali",
                "correction": [{"from": "..", "to": "."}]
            },
            {
                "code": "thai",
                "from": "Burmese",
                "to": "Thai",
                "correction": [{"from": "ึ", "to": "ิํ"}, {"from": "๚", "to": "."}]
            },
            {
                "code": "deva",
                "from": "Burmese",
                "to": "Devanagari",
                "correction": [{"from": "..", "to": "."}]
            },
            {
                "code": "khmr",
                "from": "Burmese",
                "to": "Khmer",
                "correction": [{"from": "៕", "to": "."}]
            },
            {
                "code": "lana",
                "from": "Burmese",
                "to": "TaiTham",
                "correction": [{"from": "᪩", "to": "."}]
            },
            {
                "code": "laoo",
                "from": "Burmese",
                "to": "LaoPali",
                "correction": [{"from": "ຯຯ", "to": "."}]
            },
            {
                "code": "sinh",
                "from": "Burmese",
                "to": "Sinhala",
                "correction": [{"from": "..", "to": "."}]
            }
        ]
        
        # Directory structure configuration
        self.sections = ["mula", "attha", "tika"]
        self.subsections = ["vi", "su", "bi"]
        self.sutta_subdivisions = ["di", "ma", "sa", "an", "ku"]
        
        # Markdown template for content files
        self.content_template = """---
title: {name}
sidebar: 
    order: {order}
parent: {parent}
page: {page}
---

# {name}

หน้า {page}
"""

    def _setup_paths(self):
        """Setup project paths for file generation."""
        self.project_root = Path(__file__).resolve().parent.parent.parent
        self.src_dir = self.project_root / "src" / "content" / "docs"

    def connect_database(self):
        """Establish database connection and load data."""
        self.dal = TipitakaDAL()
        self.dal.connect()
        self.db = self.dal.db
        
        # Load all required data from database
        self.category_data = self.db(self.db.category).select()
        self.books_data = self.db(self.db.books).select()
        self.tocs_data = self.db(self.db.tocs).select()
        self.pages_data = self.db(self.db.pages).select()

    def convert_text_with_aksharamukha(self, text, original_script, target_script):
        """
        Convert text using Aksharamukha transliteration.
        
        Args:
            text: Text to convert
            original_script: Source script name
            target_script: Target script name
            
        Returns:
            Converted text or original text if conversion fails
        """
        if not text or not isinstance(text, str) or text.strip() == "":
            return text
        
        try:
            converted = transliterate.process(original_script, target_script, text)
            return converted
        except Exception as e:
            print(f"Warning: Could not convert '{text[:30]}...' to {target_script}: {str(e)}")
            return text

    def apply_text_corrections(self, text, corrections):
        """
        Apply correction rules to converted text.
        
        Args:
            text: Text to correct
            corrections: List of correction rules
            
        Returns:
            Corrected text
        """
        if not text or not corrections:
            return text
        
        corrected_text = text
        for correction in corrections:
            from_text = correction.get("from", "")
            to_text = correction.get("to", "")
            if from_text:
                corrected_text = corrected_text.replace(from_text, to_text)
        
        return corrected_text

    def create_directory_structure(self):
        """Create the basic directory structure for all scripts."""
        for script in self.script_codes:
            script_dir = self.src_dir / script
            
            # Remove existing directory if it exists
            if script_dir.exists():
                shutil.rmtree(script_dir)
            
            # Create directory structure based on sections and subsections
            for section in self.sections:
                for subsection in self.subsections:
                    subsection_dir = script_dir / section / subsection
                    subsection_dir.mkdir(parents=True, exist_ok=True)
                    
                    # Create special subdirectories for 'su' (Sutta) section
                    if subsection == "su":
                        for subdivision in self.sutta_subdivisions:
                            (subsection_dir / subdivision).mkdir(exist_ok=True)

    def get_book_tocs(self, book_id):
        """
        Get table of contents entries for a specific book from tocs table.
        
        Args:
            book_id: Book ID to get TOCs for
            
        Returns:
            List of TOC entries ordered by page number
        """
        return self.db(self.db.tocs.book_id == book_id).select(
            orderby=self.db.tocs.page_number
        )

    def get_transliteration_config(self, script_code):
        """
        Get transliteration configuration for a specific script.
        
        Args:
            script_code: Target script code
            
        Returns:
            Transliteration configuration dictionary or None
        """
        return next((config for config in self.transliteration_config 
                    if config['code'] == script_code), None)

    def convert_book_content(self, book, chapters, script_code):
        """
        Convert book and chapter content to target script.
        
        Args:
            book: Book record from database
            chapters: List of chapter dictionaries
            script_code: Target script code
            
        Returns:
            Tuple of (converted_book_name, converted_book_abbr, converted_chapters)
        """
        # Default values (Myanmar script)
        book_name = book.name
        book_abbr = book.abbr
        script_chapters = [chapter.copy() for chapter in chapters]
        
        # Skip conversion for Myanmar script (original)
        if script_code == 'mymr':
            return book_name, book_abbr, script_chapters
        
        # Get transliteration configuration
        trans_config = self.get_transliteration_config(script_code)
        if not trans_config:
            return book_name, book_abbr, script_chapters
        
        # Convert book name
        book_name = self.convert_text_with_aksharamukha(
            book.name, trans_config['from'], trans_config['to']
        )
        book_name = self.apply_text_corrections(book_name, trans_config['correction'])
        
        # Convert book abbreviation
        book_abbr = self.convert_text_with_aksharamukha(
            book.abbr, trans_config['from'], trans_config['to']
        )
        book_abbr = self.apply_text_corrections(book_abbr, trans_config['correction'])
        
        # Convert chapter names
        for chapter in script_chapters:
            converted_name = self.convert_text_with_aksharamukha(
                chapter['name'], trans_config['from'], trans_config['to']
            )
            converted_name = self.apply_text_corrections(converted_name, trans_config['correction'])
            chapter['name'] = converted_name
        
        return book_name, book_abbr, script_chapters

    def determine_book_path(self, book, book_abbr, script_code):
        """
        Determine the file system path for a book based on its category.
        
        Args:
            book: Book record from database
            book_abbr: Book abbreviation (possibly converted)
            script_code: Target script code
            
        Returns:
            Path object for the book directory
        """
        base_path = self.src_dir / script_code / 'mula'
        
        if book.category in self.sutta_subdivisions:
            # Categories under 'su' (Sutta) section
            return base_path / 'su' / book.category / book_abbr
        else:
            # Other categories (vi, ab, etc.)
            return base_path / book.category / book_abbr

    def build_hierarchical_structure(self, book_tocs, book_abbr, script_code):
        """
        Build hierarchical directory structure and files based on TOC types.
        
        Args:
            book_tocs: List of TOC entries for the book
            book_abbr: Book abbreviation (converted for script)
            script_code: Target script code
            
        Returns:
            Dictionary representing the hierarchical structure
        """
        # Define type hierarchy levels
        type_hierarchy = ['chapter', 'title', 'subhead', 'subsubhead', 'subsubhead-head']
        
        # Track counters for each level (reset when going up a level)
        level_counters = {level: 0 for level in type_hierarchy}
        
        # Build structure
        structure = []
        current_path = []
        
        for toc in book_tocs:
            toc_type = toc.type
            
            # Find the level of current type
            if toc_type in type_hierarchy:
                current_level = type_hierarchy.index(toc_type)
                
                # Reset counters for deeper levels
                for i in range(current_level + 1, len(type_hierarchy)):
                    level_counters[type_hierarchy[i]] = 0
                
                # Increment counter for current level
                level_counters[toc_type] += 1
                
                # Adjust current path to match hierarchy level
                current_path = current_path[:current_level]
                current_path.append({
                    'type': toc_type,
                    'name': toc.name,
                    'page': toc.page_number,
                    'counter': level_counters[toc_type],
                    'level': current_level
                })
                
                structure.append({
                    'toc': toc,
                    'path': current_path.copy(),
                    'counter': level_counters[toc_type]
                })
        
        return structure

    def create_hierarchical_files(self, structure, book_path, book_abbr, script_code):
        """
        Create files and directories based on hierarchical structure.
        Each TOC item becomes a directory with an index.md file inside.

        Args:
            structure: Hierarchical structure from build_hierarchical_structure
            book_path: Base path for the book
            book_abbr: Book abbreviation
            script_code: Target script code
        """
        # Ensure book path exists
        book_path.mkdir(parents=True, exist_ok=True)
        
        for i, item in enumerate(structure):
            toc = item['toc']
            path_parts = item['path']
            
            if not path_parts:
                continue
                
            # Build directory path step by step
            current_dir = book_path
            parent_names = []
            
            # Create directories for all path parts
            for j, path_part in enumerate(path_parts):
                dir_name = str(path_part['counter'])
                current_dir = current_dir / dir_name
                
                # Create the directory
                current_dir.mkdir(parents=True, exist_ok=True)
                
                # Convert text if needed for this path part
                converted_name = path_part['name']
                if script_code != 'mymr':
                    trans_config = self.get_transliteration_config(script_code)
                    if trans_config:
                        converted_name = self.convert_text_with_aksharamukha(
                            path_part['name'], trans_config['from'], trans_config['to']
                        )
                        converted_name = self.apply_text_corrections(
                            converted_name, trans_config['correction']
                        )
                
                # Create index.md file in this directory
                index_file = current_dir / "index.md"
                
                # Only create index.md if it doesn't exist (avoid overwriting)
                if not index_file.exists():
                    # Prepare parent information
                    parent_info = ' > '.join(parent_names) if parent_names else book_abbr
                    
                    # Write index.md file
                    try:
                        with open(index_file, 'w', encoding='utf-8') as f:
                            f.write(self.content_template.format(
                                name=converted_name,
                                order=path_part['counter'],
                                parent=parent_info,
                                page=path_part['page']
                            ))
                    except Exception as e:
                        print(f"Error creating file {index_file}: {e}")
                        print(f"Directory exists: {current_dir.exists()}")
                        print(f"Parent directory: {current_dir}")
                        raise
                
                # Add this name to parent names for next level
                parent_names.append(converted_name)

    def process_mula_books(self):
        """Process all books with basket = 'mula' and generate files for all scripts."""
        mula_books = self.db(self.db.books.basket == 'mula').select()
        total_books = len(mula_books)
        total_scripts = len(self.script_codes)
        
        print(f"Processing {total_books} mula books across {total_scripts} scripts...")
        
        for book_idx, book in enumerate(mula_books, 1):
            print(f"\n[{book_idx}/{total_books}] Processing book: {book.name} (ID: {book.id})")
            
            # Get TOCs from tocs table
            book_tocs = self.get_book_tocs(book.id)
            toc_count = len(book_tocs)
            print(f"  └─ Found {toc_count} TOC entries")
            
            if toc_count == 0:
                print(f"  └─ No TOC entries found for book {book.id}, skipping...")
                continue
            
            # Process each script
            for script_idx, script_code in enumerate(self.script_codes, 1):
                print(f"  [{script_idx}/{total_scripts}] Converting to {script_code.upper()} script...", end=" ")
                
                # Convert book name and abbreviation
                book_name, book_abbr, _ = self.convert_book_content(
                    book, [], script_code
                )
                
                # Determine base book path
                book_path = self.determine_book_path(book, book_abbr, script_code)
                
                # Build hierarchical structure
                structure = self.build_hierarchical_structure(book_tocs, book_abbr, script_code)
                
                # Create files and directories
                self.create_hierarchical_files(structure, book_path, book_abbr, script_code)
                
                print("✓ Complete")
        
        print(f"\nAll {total_books} books processed successfully across {total_scripts} scripts!")

    def build(self):
        """
        Main build process - execute all steps to generate documentation files.
        
        This method orchestrates the entire build process:
        1. Connect to database
        2. Create directory structure
        3. Process and convert content
        4. Generate Markdown files
        """
        print("Starting Tipitaka documentation build process...")
        
        # Step 1: Connect to database and load data
        print("Connecting to database...")
        self.connect_database()
        
        # Step 2: Create directory structure
        print("Creating directory structure...")
        self.create_directory_structure()
        
        # Step 3: Process books and generate files
        print("Processing books and generating files...")
        self.process_mula_books()
        
        print("Build process completed successfully!")


# === Main Execution ===
if __name__ == "__main__":
    builder = TipitakaBuilder()
    builder.build()
