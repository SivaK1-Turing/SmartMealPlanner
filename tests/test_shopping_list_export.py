"""
Tests for the shopping list export module.
"""

import pytest
import json
import csv
from datetime import date
from io import StringIO
from unittest.mock import patch, mock_open

from mealplanner.shopping_list import ShoppingList, ShoppingListItem
from mealplanner.shopping_list_export import ShoppingListExporter


class TestShoppingListExporter:
    """Test the ShoppingListExporter class."""
    
    def setup_method(self):
        """Set up test data."""
        self.items = [
            ShoppingListItem(
                ingredient_id=1,
                ingredient_name="Chicken Breast",
                category="Meat",
                total_quantity=500.0,
                unit="grams",
                recipes_used=["Grilled Chicken", "Chicken Salad"]
            ),
            ShoppingListItem(
                ingredient_id=2,
                ingredient_name="Rice",
                category="Grains",
                total_quantity=200.0,
                unit="grams",
                recipes_used=["Rice Bowl"]
            ),
            ShoppingListItem(
                ingredient_id=3,
                ingredient_name="Tomatoes",
                category="Vegetables",
                total_quantity=300.0,
                unit="grams",
                recipes_used=["Salad", "Pasta Sauce"],
                notes="Organic preferred"
            )
        ]
        
        self.shopping_list = ShoppingList(
            start_date=date(2024, 1, 15),
            end_date=date(2024, 1, 16),
            items=self.items,
            total_recipes=3,
            total_meals=4,
            categories=["Meat", "Grains", "Vegetables"]
        )
    
    def test_export_to_text_grouped(self):
        """Test exporting to text format with category grouping."""
        result = ShoppingListExporter.export_to_text(
            self.shopping_list,
            group_by_category=True,
            include_recipes=True,
            include_summary=True
        )
        
        assert "🛒 SHOPPING LIST" in result
        assert "2024-01-15 to 2024-01-16" in result
        assert "Total Meals: 4" in result
        assert "Total Recipes: 3" in result
        assert "Total Items: 3" in result
        
        # Check category grouping
        assert "📂 GRAINS" in result
        assert "📂 MEAT" in result
        assert "📂 VEGETABLES" in result
        
        # Check items
        assert "Chicken Breast - 500 grams" in result
        assert "Rice - 200 grams" in result
        assert "Tomatoes - 300 grams" in result
        
        # Check recipe information
        assert "Grilled Chicken, Chicken Salad" in result
        assert "Rice Bowl" in result
        
        # Check notes
        assert "Organic preferred" in result
    
    def test_export_to_text_ungrouped(self):
        """Test exporting to text format without category grouping."""
        result = ShoppingListExporter.export_to_text(
            self.shopping_list,
            group_by_category=False,
            include_recipes=False,
            include_summary=False
        )
        
        assert "🛍️ SHOPPING ITEMS" in result
        assert "📂 GRAINS" not in result  # No category headers
        assert "Total Meals:" not in result  # No summary
        assert "Grilled Chicken" not in result  # No recipe info
    
    def test_export_to_text_empty_list(self):
        """Test exporting empty shopping list to text."""
        empty_list = ShoppingList(
            start_date=date(2024, 1, 15),
            end_date=date(2024, 1, 15),
            items=[],
            total_recipes=0,
            total_meals=0,
            categories=[]
        )
        
        result = ShoppingListExporter.export_to_text(empty_list)
        
        assert "🛒 SHOPPING LIST" in result
        assert "No items in shopping list." in result
    
    def test_export_to_csv(self):
        """Test exporting to CSV format."""
        result = ShoppingListExporter.export_to_csv(self.shopping_list)
        
        # Parse CSV to verify content
        reader = csv.reader(StringIO(result))
        rows = list(reader)
        
        # Check header
        assert rows[0] == ['Item Name', 'Quantity', 'Unit', 'Category', 'Recipes Used', 'Notes']
        
        # Check data rows
        assert len(rows) == 4  # Header + 3 items
        
        # Check first item
        assert rows[1][0] == "Chicken Breast"
        assert rows[1][1] == "500"
        assert rows[1][2] == "grams"
        assert rows[1][3] == "Meat"
        assert "Grilled Chicken" in rows[1][4]
        assert "Chicken Salad" in rows[1][4]
        
        # Check item with notes
        tomato_row = next(row for row in rows if row[0] == "Tomatoes")
        assert tomato_row[5] == "Organic preferred"
    
    def test_export_to_json_with_metadata(self):
        """Test exporting to JSON format with metadata."""
        result = ShoppingListExporter.export_to_json(
            self.shopping_list,
            include_metadata=True
        )
        
        data = json.loads(result)
        
        assert data['start_date'] == "2024-01-15"
        assert data['end_date'] == "2024-01-16"
        assert data['total_recipes'] == 3
        assert data['total_meals'] == 4
        assert data['total_items'] == 3
        assert len(data['items']) == 3
        assert data['categories'] == ["Meat", "Grains", "Vegetables"]
        
        # Check first item
        chicken_item = next(item for item in data['items'] if item['ingredient_name'] == "Chicken Breast")
        assert chicken_item['ingredient_id'] == 1
        assert chicken_item['total_quantity'] == 500.0
        assert chicken_item['unit'] == "grams"
        assert chicken_item['category'] == "Meat"
        assert len(chicken_item['recipes_used']) == 2
    
    def test_export_to_json_without_metadata(self):
        """Test exporting to JSON format without metadata."""
        result = ShoppingListExporter.export_to_json(
            self.shopping_list,
            include_metadata=False
        )
        
        data = json.loads(result)
        
        assert 'start_date' not in data
        assert 'total_recipes' not in data
        assert 'items' in data
        assert 'total_items' in data
        assert len(data['items']) == 3
    
    def test_export_to_markdown_grouped(self):
        """Test exporting to Markdown format with grouping."""
        result = ShoppingListExporter.export_to_markdown(
            self.shopping_list,
            group_by_category=True,
            include_recipes=True
        )
        
        assert "# 🛒 Shopping List" in result
        assert "**📅 Date Range:** 2024-01-15 to 2024-01-16" in result
        assert "**🍽️ Total Meals:** 4" in result
        
        # Check category headers
        assert "## 📂 Grains" in result
        assert "## 📂 Meat" in result
        assert "## 📂 Vegetables" in result
        
        # Check items with markdown formatting
        assert "- **Chicken Breast** - 500 grams" in result
        assert "*(used in: Grilled Chicken, Chicken Salad)*" in result
        assert "- *Organic preferred*" in result
    
    def test_export_to_markdown_ungrouped(self):
        """Test exporting to Markdown format without grouping."""
        result = ShoppingListExporter.export_to_markdown(
            self.shopping_list,
            group_by_category=False,
            include_recipes=False
        )
        
        assert "## 🛍️ Items" in result
        assert "## 📂" not in result  # No category headers
        assert "*(used in:" not in result  # No recipe info
    
    def test_create_printable_list_with_checkboxes(self):
        """Test creating printable list with checkboxes."""
        result = ShoppingListExporter.create_printable_list(
            self.shopping_list,
            checkboxes=True,
            group_by_category=True
        )
        
        assert "SHOPPING LIST" in result
        assert "01/15 - 01/16/2024" in result
        assert "Items: 3" in result
        
        # Check category grouping
        assert "MEAT" in result
        assert "GRAINS" in result
        assert "VEGETABLES" in result
        
        # Check checkboxes
        assert "☐ Chicken Breast (500 grams)" in result
        assert "☐ Rice (200 grams)" in result
        assert "☐ Tomatoes (300 grams)" in result
    
    def test_create_printable_list_without_checkboxes(self):
        """Test creating printable list without checkboxes."""
        result = ShoppingListExporter.create_printable_list(
            self.shopping_list,
            checkboxes=False,
            group_by_category=False
        )
        
        assert "☐" not in result  # No checkboxes
        assert "MEAT" not in result  # No category grouping
        assert "Chicken Breast (500 grams)" in result
    
    def test_create_printable_list_single_date(self):
        """Test creating printable list for single date."""
        single_date_list = ShoppingList(
            start_date=date(2024, 1, 15),
            end_date=date(2024, 1, 15),
            items=self.items[:1],
            total_recipes=1,
            total_meals=1,
            categories=["Meat"]
        )
        
        result = ShoppingListExporter.create_printable_list(single_date_list)
        
        assert "01/15/2024" in result  # Single date format
        assert "01/15 - " not in result  # Not date range format
    
    def test_create_printable_list_empty(self):
        """Test creating printable list with no items."""
        empty_list = ShoppingList(
            start_date=date(2024, 1, 15),
            end_date=date(2024, 1, 15),
            items=[],
            total_recipes=0,
            total_meals=0,
            categories=[]
        )
        
        result = ShoppingListExporter.create_printable_list(empty_list)
        
        assert "No items to buy." in result
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_save_to_file_text(self, mock_mkdir, mock_file):
        """Test saving shopping list to text file."""
        success = ShoppingListExporter.save_to_file(
            self.shopping_list,
            "test_list.txt",
            "text",
            group_by_category=True
        )
        
        assert success
        mock_file.assert_called_once()
        mock_mkdir.assert_called_once()
        
        # Check that text content was written
        written_content = mock_file().write.call_args[0][0]
        assert "🛒 SHOPPING LIST" in written_content
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_save_to_file_csv(self, mock_mkdir, mock_file):
        """Test saving shopping list to CSV file."""
        success = ShoppingListExporter.save_to_file(
            self.shopping_list,
            "test_list.csv",
            "csv"
        )
        
        assert success
        mock_file.assert_called_once()
        
        # Check that CSV content was written
        written_content = mock_file().write.call_args[0][0]
        assert "Item Name,Quantity,Unit,Category,Recipes Used,Notes" in written_content
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_save_to_file_json(self, mock_mkdir, mock_file):
        """Test saving shopping list to JSON file."""
        success = ShoppingListExporter.save_to_file(
            self.shopping_list,
            "test_list.json",
            "json"
        )
        
        assert success
        mock_file.assert_called_once()
        
        # Check that JSON content was written
        written_content = mock_file().write.call_args[0][0]
        data = json.loads(written_content)
        assert data['total_items'] == 3
    
    @patch('builtins.open', new_callable=mock_open)
    @patch('pathlib.Path.mkdir')
    def test_save_to_file_markdown(self, mock_mkdir, mock_file):
        """Test saving shopping list to Markdown file."""
        success = ShoppingListExporter.save_to_file(
            self.shopping_list,
            "test_list.md",
            "markdown"
        )
        
        assert success
        mock_file.assert_called_once()
        
        # Check that Markdown content was written
        written_content = mock_file().write.call_args[0][0]
        assert "# 🛒 Shopping List" in written_content
    
    def test_save_to_file_unsupported_format(self):
        """Test saving with unsupported format."""
        success = ShoppingListExporter.save_to_file(
            self.shopping_list,
            "test_list.xyz",
            "unsupported"
        )
        
        assert not success
    
    @patch('builtins.open', side_effect=IOError("Permission denied"))
    def test_save_to_file_error(self, mock_file):
        """Test saving file with IO error."""
        success = ShoppingListExporter.save_to_file(
            self.shopping_list,
            "test_list.txt",
            "text"
        )
        
        assert not success
    
    def test_quantity_formatting(self):
        """Test that quantities are formatted correctly (removing trailing zeros)."""
        items_with_decimals = [
            ShoppingListItem(1, "Item 1", "Category", 1.0, "units", []),
            ShoppingListItem(2, "Item 2", "Category", 1.5, "units", []),
            ShoppingListItem(3, "Item 3", "Category", 2.25, "units", [])
        ]
        
        test_list = ShoppingList(
            start_date=date(2024, 1, 15),
            end_date=date(2024, 1, 15),
            items=items_with_decimals,
            total_recipes=1,
            total_meals=1,
            categories=["Category"]
        )
        
        result = ShoppingListExporter.export_to_text(test_list)
        
        assert "Item 1 - 1 units" in result  # 1.0 -> 1
        assert "Item 2 - 1.5 units" in result  # 1.5 stays as is
        assert "Item 3 - 2.2 units" in result  # 2.25 -> 2.2 (rounded to 1 decimal)
