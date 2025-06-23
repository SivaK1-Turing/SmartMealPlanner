"""
Shopping list export functionality for the Smart Meal Planner application.

Handles exporting shopping lists to various formats.
"""

import logging
import json
import csv
from datetime import date
from typing import List, Optional, Dict, Any
from pathlib import Path
from io import StringIO

from .shopping_list import ShoppingList, ShoppingListItem

logger = logging.getLogger(__name__)


class ShoppingListExporter:
    """Exports shopping lists to various formats."""
    
    @staticmethod
    def export_to_text(
        shopping_list: ShoppingList,
        group_by_category: bool = True,
        include_recipes: bool = True,
        include_summary: bool = True
    ) -> str:
        """
        Export shopping list to formatted text.
        
        Args:
            shopping_list: Shopping list to export
            group_by_category: Whether to group items by category
            include_recipes: Whether to include recipe information
            include_summary: Whether to include summary information
            
        Returns:
            Formatted text string
        """
        lines = []
        
        # Header
        if shopping_list.start_date == shopping_list.end_date:
            date_range = shopping_list.start_date.strftime("%Y-%m-%d")
        else:
            date_range = f"{shopping_list.start_date.strftime('%Y-%m-%d')} to {shopping_list.end_date.strftime('%Y-%m-%d')}"
        
        lines.append("🛒 SHOPPING LIST")
        lines.append("=" * 50)
        lines.append(f"📅 Date Range: {date_range}")
        
        if include_summary:
            lines.append(f"🍽️ Total Meals: {shopping_list.total_meals}")
            lines.append(f"📖 Total Recipes: {shopping_list.total_recipes}")
            lines.append(f"🛍️ Total Items: {len(shopping_list.items)}")
        
        lines.append("")
        
        if not shopping_list.items:
            lines.append("No items in shopping list.")
            return "\n".join(lines)
        
        # Group items by category if requested
        if group_by_category:
            # Group items by category
            categorized_items = {}
            for item in shopping_list.items:
                category = item.category or "Other"
                if category not in categorized_items:
                    categorized_items[category] = []
                categorized_items[category].append(item)
            
            # Sort categories
            sorted_categories = sorted(categorized_items.keys())
            
            for category in sorted_categories:
                lines.append(f"📂 {category.upper()}")
                lines.append("-" * 30)
                
                for item in categorized_items[category]:
                    quantity_str = f"{item.total_quantity:.1f}".rstrip('0').rstrip('.')
                    line = f"  • {item.ingredient_name} - {quantity_str} {item.unit}"
                    
                    if include_recipes and item.recipes_used:
                        recipes_str = ", ".join(item.recipes_used[:3])  # Limit to 3 recipes
                        if len(item.recipes_used) > 3:
                            recipes_str += f" (+{len(item.recipes_used) - 3} more)"
                        line += f" ({recipes_str})"
                    
                    if item.notes:
                        line += f" - {item.notes}"
                    
                    lines.append(line)
                
                lines.append("")
        else:
            # Simple list without categories
            lines.append("🛍️ SHOPPING ITEMS")
            lines.append("-" * 30)
            
            for item in shopping_list.items:
                quantity_str = f"{item.total_quantity:.1f}".rstrip('0').rstrip('.')
                line = f"• {item.ingredient_name} - {quantity_str} {item.unit}"
                
                if include_recipes and item.recipes_used:
                    recipes_str = ", ".join(item.recipes_used[:2])
                    if len(item.recipes_used) > 2:
                        recipes_str += f" (+{len(item.recipes_used) - 2} more)"
                    line += f" ({recipes_str})"
                
                if item.notes:
                    line += f" - {item.notes}"
                
                lines.append(line)
        
        return "\n".join(lines)
    
    @staticmethod
    def export_to_csv(shopping_list: ShoppingList) -> str:
        """
        Export shopping list to CSV format.
        
        Args:
            shopping_list: Shopping list to export
            
        Returns:
            CSV string
        """
        output = StringIO()
        writer = csv.writer(output)
        
        # Header
        writer.writerow([
            'Item Name',
            'Quantity',
            'Unit',
            'Category',
            'Recipes Used',
            'Notes'
        ])
        
        # Data rows
        for item in shopping_list.items:
            quantity_str = f"{item.total_quantity:.2f}".rstrip('0').rstrip('.')
            recipes_str = "; ".join(item.recipes_used) if item.recipes_used else ""
            
            writer.writerow([
                item.ingredient_name,
                quantity_str,
                item.unit,
                item.category or "",
                recipes_str,
                item.notes or ""
            ])
        
        return output.getvalue()
    
    @staticmethod
    def export_to_json(shopping_list: ShoppingList, include_metadata: bool = True) -> str:
        """
        Export shopping list to JSON format.
        
        Args:
            shopping_list: Shopping list to export
            include_metadata: Whether to include metadata
            
        Returns:
            JSON string
        """
        data = shopping_list.to_dict()
        
        if not include_metadata:
            # Keep only essential data
            data = {
                'items': data['items'],
                'total_items': data['total_items']
            }
        
        return json.dumps(data, indent=2, default=str)
    
    @staticmethod
    def export_to_markdown(
        shopping_list: ShoppingList,
        group_by_category: bool = True,
        include_recipes: bool = True
    ) -> str:
        """
        Export shopping list to Markdown format.
        
        Args:
            shopping_list: Shopping list to export
            group_by_category: Whether to group items by category
            include_recipes: Whether to include recipe information
            
        Returns:
            Markdown string
        """
        lines = []
        
        # Header
        lines.append("# 🛒 Shopping List")
        lines.append("")
        
        if shopping_list.start_date == shopping_list.end_date:
            date_range = shopping_list.start_date.strftime("%Y-%m-%d")
        else:
            date_range = f"{shopping_list.start_date.strftime('%Y-%m-%d')} to {shopping_list.end_date.strftime('%Y-%m-%d')}"
        
        lines.append(f"**📅 Date Range:** {date_range}")
        lines.append(f"**🍽️ Total Meals:** {shopping_list.total_meals}")
        lines.append(f"**📖 Total Recipes:** {shopping_list.total_recipes}")
        lines.append(f"**🛍️ Total Items:** {len(shopping_list.items)}")
        lines.append("")
        
        if not shopping_list.items:
            lines.append("*No items in shopping list.*")
            return "\n".join(lines)
        
        if group_by_category:
            # Group items by category
            categorized_items = {}
            for item in shopping_list.items:
                category = item.category or "Other"
                if category not in categorized_items:
                    categorized_items[category] = []
                categorized_items[category].append(item)
            
            # Sort categories
            sorted_categories = sorted(categorized_items.keys())
            
            for category in sorted_categories:
                lines.append(f"## 📂 {category}")
                lines.append("")
                
                for item in categorized_items[category]:
                    quantity_str = f"{item.total_quantity:.1f}".rstrip('0').rstrip('.')
                    line = f"- **{item.ingredient_name}** - {quantity_str} {item.unit}"
                    
                    if include_recipes and item.recipes_used:
                        recipes_str = ", ".join(item.recipes_used)
                        line += f" *(used in: {recipes_str})*"
                    
                    if item.notes:
                        line += f" - *{item.notes}*"
                    
                    lines.append(line)
                
                lines.append("")
        else:
            # Simple list
            lines.append("## 🛍️ Items")
            lines.append("")
            
            for item in shopping_list.items:
                quantity_str = f"{item.total_quantity:.1f}".rstrip('0').rstrip('.')
                line = f"- **{item.ingredient_name}** - {quantity_str} {item.unit}"
                
                if include_recipes and item.recipes_used:
                    recipes_str = ", ".join(item.recipes_used)
                    line += f" *(used in: {recipes_str})*"
                
                if item.notes:
                    line += f" - *{item.notes}*"
                
                lines.append(line)
        
        return "\n".join(lines)
    
    @staticmethod
    def save_to_file(
        shopping_list: ShoppingList,
        file_path: str,
        format_type: str = "text",
        **kwargs
    ) -> bool:
        """
        Save shopping list to a file.
        
        Args:
            shopping_list: Shopping list to save
            file_path: Path to save the file
            format_type: Export format ('text', 'csv', 'json', 'markdown')
            **kwargs: Additional arguments for export functions
            
        Returns:
            True if successful, False otherwise
        """
        try:
            path = Path(file_path)
            
            if format_type.lower() == "text":
                content = ShoppingListExporter.export_to_text(shopping_list, **kwargs)
            elif format_type.lower() == "csv":
                content = ShoppingListExporter.export_to_csv(shopping_list)
            elif format_type.lower() == "json":
                content = ShoppingListExporter.export_to_json(shopping_list, **kwargs)
            elif format_type.lower() == "markdown":
                content = ShoppingListExporter.export_to_markdown(shopping_list, **kwargs)
            else:
                logger.error(f"Unsupported format type: {format_type}")
                return False
            
            # Create directory if it doesn't exist
            path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write content to file
            with open(path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            logger.info(f"Shopping list saved to {file_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving shopping list to {file_path}: {e}")
            return False
    
    @staticmethod
    def create_printable_list(
        shopping_list: ShoppingList,
        checkboxes: bool = True,
        group_by_category: bool = True
    ) -> str:
        """
        Create a printable shopping list with checkboxes.
        
        Args:
            shopping_list: Shopping list to format
            checkboxes: Whether to include checkboxes
            group_by_category: Whether to group by category
            
        Returns:
            Printable formatted string
        """
        lines = []
        
        # Header
        lines.append("SHOPPING LIST")
        lines.append("=" * 40)
        
        if shopping_list.start_date == shopping_list.end_date:
            date_range = shopping_list.start_date.strftime("%m/%d/%Y")
        else:
            start_str = shopping_list.start_date.strftime("%m/%d")
            end_str = shopping_list.end_date.strftime("%m/%d/%Y")
            date_range = f"{start_str} - {end_str}"
        
        lines.append(f"Date: {date_range}")
        lines.append(f"Items: {len(shopping_list.items)}")
        lines.append("")
        
        if not shopping_list.items:
            lines.append("No items to buy.")
            return "\n".join(lines)
        
        checkbox = "☐ " if checkboxes else ""
        
        if group_by_category:
            # Group by category
            categorized_items = {}
            for item in shopping_list.items:
                category = item.category or "Other"
                if category not in categorized_items:
                    categorized_items[category] = []
                categorized_items[category].append(item)
            
            for category in sorted(categorized_items.keys()):
                lines.append(f"{category.upper()}")
                lines.append("-" * 20)
                
                for item in categorized_items[category]:
                    quantity_str = f"{item.total_quantity:.1f}".rstrip('0').rstrip('.')
                    lines.append(f"{checkbox}{item.ingredient_name} ({quantity_str} {item.unit})")
                
                lines.append("")
        else:
            for item in shopping_list.items:
                quantity_str = f"{item.total_quantity:.1f}".rstrip('0').rstrip('.')
                lines.append(f"{checkbox}{item.ingredient_name} ({quantity_str} {item.unit})")
        
        return "\n".join(lines)
