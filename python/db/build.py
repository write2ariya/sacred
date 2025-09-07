import shutil
import re
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
        
        # Markdown template for chapter files
        self.chapter_template = """---
title: {name}
sidebar: 
    order: {order}
page: {page_range}
paranum: {paranum_list}
---

# {name}

{content}
"""

        # Template for page files
        self.page_template = """---
title: "{chapter_name} - หน้า {page_num}"
sidebar: 
    order: {order}
page: {page_num}
paranum: {paranum}
---

# {chapter_name}
## หน้า {page_num}

{content}
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

    def convert_html_content(self, html_content, script_code):
        """
        Convert text content within HTML tags while preserving HTML structure.
        
        Args:
            html_content: HTML content string
            script_code: Target script code
            
        Returns:
            HTML content with converted text
        """
        if not html_content or script_code == 'mymr':
            return html_content
        
        # Get transliteration configuration
        trans_config = self.get_transliteration_config(script_code)
        if not trans_config:
            return html_content
        
        def convert_text_match(match):
            """Convert text content between HTML tags."""
            text_content = match.group(0)
            
            # Skip if it's only whitespace or empty
            if not text_content.strip():
                return text_content
            
            # Convert the text
            converted = self.convert_text_with_aksharamukha(
                text_content, trans_config['from'], trans_config['to']
            )
            converted = self.apply_text_corrections(converted, trans_config['correction'])
            
            return converted
        
        # Pattern to match text content between HTML tags
        # This matches text that is not inside < > brackets
        pattern = r'(?<=>)[^<]+(?=<)|(?<=>)[^<]+$|^[^<]+(?=<)'
        
        try:
            # Convert text content while preserving HTML structure
            converted_html = re.sub(pattern, convert_text_match, html_content)
            return converted_html
        except Exception as e:
            print(f"Warning: Could not convert HTML content for {script_code}: {str(e)}")
            return html_content

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

    def parse_book_chapters(self, book_toc):
        """
        Parse table of contents to extract chapter information.
        
        Args:
            book_toc: Table of contents string from book record
            
        Returns:
            List of chapter dictionaries with name and page information
        """
        chapters = []
        if not book_toc:
            return chapters
            
        toc_lines = book_toc.split('\n')
        for line in toc_lines:
            if line.strip().startswith('chapter->'):
                parts = line.strip().split('->')
                if len(parts) >= 3:
                    chapter_name = parts[1]
                    page_number = int(parts[2])
                    chapters.append({
                        "name": chapter_name,
                        "page": page_number
                    })
        
        return chapters

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

    def get_chapter_pages(self, book_id, start_page, end_page):
        """
        Get pages content for a specific chapter range.
        
        Args:
            book_id: Book ID to filter pages
            start_page: Starting page number (inclusive)
            end_page: Ending page number (exclusive, None for last chapter)
            
        Returns:
            List of page records sorted by page number
        """
        query = (self.db.pages.bookid == book_id) & (self.db.pages.page >= start_page)
        
        if end_page is not None:
            query = query & (self.db.pages.page < end_page)
        
        pages = self.db(query).select(orderby=self.db.pages.page)
        return pages

    def format_chapter_content(self, pages, chapter_name, script_code):
        """
        Format pages content into markdown with page separators and script conversion.
        
        Args:
            pages: List of page records
            chapter_name: Name of the chapter
            script_code: Target script code for content conversion
            
        Returns:
            Tuple of (formatted_content, paranum_list, page_range)
        """
        if not pages:
            return "ไม่มีเนื้อหา", [], "N/A"
        
        content_parts = []
        paranum_list = []
        
        for page in pages:
            # Add page separator comment
            content_parts.append(f"<!-- หน้า {page.page} -->")
            
            # Add page content with script conversion
            if page.content:
                # Convert HTML content to target script
                converted_content = self.convert_html_content(page.content, script_code)
                content_parts.append(converted_content)
            else:
                content_parts.append("<!-- ไม่มีเนื้อหาในหน้านี้ -->")
            
            # Collect paranum
            if page.paranum:
                paranum_list.append(page.paranum)
            
            # Add spacing between pages
            content_parts.append("")
        
        # Create page range string
        first_page = pages[0].page
        last_page = pages[-1].page
        page_range = f"{first_page}-{last_page}" if first_page != last_page else str(first_page)
        
        formatted_content = "\n".join(content_parts)
        
        return formatted_content, paranum_list, page_range

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

    def create_chapter_files(self, book_path, chapters, book_id, book_lastpage, script_code):
        """
        Create Markdown files for each chapter with individual page files to avoid memory issues.
        
        Args:
            book_path: Path to the book directory
            chapters: List of chapter dictionaries
            book_id: Book ID for querying pages
            book_lastpage: Last page number of the book
            script_code: Target script code for content conversion
        """
        book_path.mkdir(parents=True, exist_ok=True)
        
        for index, chapter in enumerate(chapters, 1):
            # Determine page range for this chapter
            start_page = chapter['page']
            
            # End page is the start of next chapter, or book's last page for final chapter
            if index < len(chapters):
                end_page = chapters[index]['page']  # Next chapter's start page
            else:
                end_page = book_lastpage + 1  # Last chapter goes to end of book
            
            # Get pages content for this chapter
            pages = self.get_chapter_pages(book_id, start_page, end_page)
            
            # Create chapter directory
            chapter_dir = book_path / str(index)
            chapter_dir.mkdir(exist_ok=True)
            
            # Create index file for chapter
            chapter_index_file = chapter_dir / "index.md"
            page_range = f"{start_page}-{end_page-1}" if start_page != end_page-1 else str(start_page)
            
            with open(chapter_index_file, 'w', encoding='utf-8') as file:
                file.write(f"""---
title: {chapter['name']}
sidebar: 
    order: {index}
page: {page_range}
---

# {chapter['name']}

บทนี้มี {len(pages)} หน้า (หน้า {start_page}-{end_page-1})

""")
            
            # Create individual page files
            for page_index, page in enumerate(pages, 1):
                if page.content:
                    # Convert HTML content to target script
                    converted_content = self.convert_html_content(page.content, script_code)
                    
                    # Create page file
                    page_file = chapter_dir / f"page-{page.page}.md"
                    with open(page_file, 'w', encoding='utf-8') as file:
                        file.write(self.page_template.format(
                            chapter_name=chapter['name'],
                            page_num=page.page,
                            order=page_index,
                            paranum=page.paranum or "",
                            content=converted_content
                        ))

    def process_mula_books(self):
        """Process all books with basket = 'mula' and generate files for all scripts."""
        mula_books = self.db(self.db.books.basket == 'mula').select()
        
        for book in mula_books:
            # Parse chapters from table of contents
            book_chapters = self.parse_book_chapters(book.toc)
            
            # Process each script
            for script_code in self.script_codes:
                # Convert content to target script
                book_name, book_abbr, script_chapters = self.convert_book_content(
                    book, book_chapters, script_code
                )
                
                # Determine file path
                book_path = self.determine_book_path(book, book_abbr, script_code)
                
                # Create chapter files with actual content
                self.create_chapter_files(book_path, script_chapters, book.id, book.lastpage, script_code)

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
