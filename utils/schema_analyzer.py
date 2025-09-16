"""
Database Schema Analyzer Utility
Helps analyze and optimize database schemas for GenBI
"""

import pandas as pd
from typing import Dict, List, Any, Tuple
from database.connection_manager import db_manager
from semantic_layer.vector_store import semantic_layer
import json
import logging

logger = logging.getLogger(__name__)

class SchemaAnalyzer:
    def __init__(self):
        self.schema_info = {}
        self.analysis_results = {}
    
    def analyze_database_schema(self, connection_name: str = "default") -> Dict[str, Any]:
        """Comprehensive database schema analysis"""
        try:
            # Get schema information
            self.schema_info = db_manager.get_table_schema(connection_name)
            
            analysis = {
                "summary": self._get_schema_summary(),
                "table_analysis": self._analyze_tables(),
                "relationship_analysis": self._analyze_relationships(),
                "complexity_analysis": self._analyze_complexity(),
                "recommendations": self._generate_recommendations()
            }
            
            self.analysis_results = analysis
            return analysis
            
        except Exception as e:
            logger.error(f"Schema analysis failed: {str(e)}")
            return {"error": str(e)}
    
    def _get_schema_summary(self) -> Dict[str, Any]:
        """Get high-level schema summary"""
        total_tables = len(self.schema_info)
        total_columns = sum(len(table['columns']) for table in self.schema_info.values())
        
        # Column type distribution
        type_counts = {}
        for table_info in self.schema_info.values():
            for col in table_info['columns']:
                col_type = str(col['type']).lower()
                type_counts[col_type] = type_counts.get(col_type, 0) + 1
        
        return {
            "total_tables": total_tables,
            "total_columns": total_columns,
            "avg_columns_per_table": total_columns / total_tables if total_tables > 0 else 0,
            "column_type_distribution": type_counts
        }
    
    def _analyze_tables(self) -> List[Dict[str, Any]]:
        """Analyze individual tables"""
        table_analysis = []
        
        for table_name, table_info in self.schema_info.items():
            columns = table_info['columns']
            
            # Column analysis
            numeric_cols = [col for col in columns if 'int' in str(col['type']).lower() or 'float' in str(col['type']).lower() or 'decimal' in str(col['type']).lower()]
            text_cols = [col for col in columns if 'varchar' in str(col['type']).lower() or 'text' in str(col['type']).lower() or 'char' in str(col['type']).lower()]
            date_cols = [col for col in columns if 'date' in str(col['type']).lower() or 'time' in str(col['type']).lower()]
            
            # Primary keys
            primary_keys = [col for col in columns if col.get('primary_key', False)]
            
            # Foreign keys
            foreign_keys = table_info.get('foreign_keys', [])
            
            analysis = {
                "table_name": table_name,
                "total_columns": len(columns),
                "numeric_columns": len(numeric_cols),
                "text_columns": len(text_cols),
                "date_columns": len(date_cols),
                "primary_keys": len(primary_keys),
                "foreign_keys": len(foreign_keys),
                "complexity_score": self._calculate_table_complexity(table_info),
                "column_details": {
                    "numeric": [col['name'] for col in numeric_cols],
                    "text": [col['name'] for col in text_cols],
                    "date": [col['name'] for col in date_cols]
                }
            }
            
            table_analysis.append(analysis)
        
        return sorted(table_analysis, key=lambda x: x['complexity_score'], reverse=True)
    
    def _analyze_relationships(self) -> Dict[str, Any]:
        """Analyze table relationships"""
        relationships = []
        table_connections = {}
        
        for table_name, table_info in self.schema_info.items():
            table_connections[table_name] = {
                'outgoing': [],  # Foreign keys from this table
                'incoming': []   # Foreign keys to this table
            }
            
            for fk in table_info.get('foreign_keys', []):
                relationship = {
                    'source_table': table_name,
                    'source_column': fk['constrained_columns'][0] if fk['constrained_columns'] else None,
                    'target_table': fk['referred_table'],
                    'target_column': fk['referred_columns'][0] if fk['referred_columns'] else None
                }
                relationships.append(relationship)
                table_connections[table_name]['outgoing'].append(fk['referred_table'])
        
        # Calculate incoming relationships
        for rel in relationships:
            target_table = rel['target_table']
            if target_table in table_connections:
                table_connections[target_table]['incoming'].append(rel['source_table'])
        
        # Find central tables (highly connected)
        connection_scores = {}
        for table, connections in table_connections.items():
            score = len(connections['outgoing']) + len(connections['incoming'])
            connection_scores[table] = score
        
        return {
            "total_relationships": len(relationships),
            "relationships": relationships,
            "table_connections": table_connections,
            "most_connected_tables": sorted(connection_scores.items(), key=lambda x: x[1], reverse=True)[:10]
        }
    
    def _analyze_complexity(self) -> Dict[str, Any]:
        """Analyze schema complexity for GenBI optimization"""
        complexity_metrics = {}
        
        # Table complexity distribution
        table_complexities = []
        for table_name, table_info in self.schema_info.items():
            complexity = self._calculate_table_complexity(table_info)
            table_complexities.append(complexity)
        
        # Overall complexity metrics
        avg_complexity = sum(table_complexities) / len(table_complexities) if table_complexities else 0
        max_complexity = max(table_complexities) if table_complexities else 0
        
        # High-dimensional tables (>50 columns)
        high_dim_tables = [
            table_name for table_name, table_info in self.schema_info.items()
            if len(table_info['columns']) > 50
        ]
        
        complexity_metrics = {
            "average_table_complexity": avg_complexity,
            "maximum_table_complexity": max_complexity,
            "high_dimensional_tables": high_dim_tables,
            "complexity_distribution": {
                "low": len([c for c in table_complexities if c < 20]),
                "medium": len([c for c in table_complexities if 20 <= c < 50]),
                "high": len([c for c in table_complexities if c >= 50])
            }
        }
        
        return complexity_metrics
    
    def _calculate_table_complexity(self, table_info: Dict) -> float:
        """Calculate complexity score for a table"""
        columns = table_info['columns']
        foreign_keys = table_info.get('foreign_keys', [])
        
        # Base complexity from column count
        base_score = len(columns)
        
        # Add complexity for relationships
        relationship_score = len(foreign_keys) * 2
        
        # Add complexity for data types
        type_complexity = 0
        for col in columns:
            col_type = str(col['type']).lower()
            if 'json' in col_type or 'xml' in col_type:
                type_complexity += 3
            elif 'text' in col_type or 'blob' in col_type:
                type_complexity += 2
            elif 'varchar' in col_type:
                type_complexity += 1
        
        return base_score + relationship_score + type_complexity
    
    def _generate_recommendations(self) -> List[Dict[str, str]]:
        """Generate optimization recommendations"""
        recommendations = []
        
        if not self.schema_info:
            return recommendations
        
        # Check for high-dimensional tables
        high_dim_tables = [
            table_name for table_name, table_info in self.schema_info.items()
            if len(table_info['columns']) > 100
        ]
        
        if high_dim_tables:
            recommendations.append({
                "type": "performance",
                "priority": "high",
                "title": "High-Dimensional Tables Detected",
                "description": f"Tables {', '.join(high_dim_tables[:3])} have >100 columns. Consider using semantic layer optimization.",
                "action": "Enable vector-based column selection for these tables"
            })
        
        # Check for missing relationships
        tables_without_fks = [
            table_name for table_name, table_info in self.schema_info.items()
            if not table_info.get('foreign_keys', [])
        ]
        
        if len(tables_without_fks) > len(self.schema_info) * 0.5:
            recommendations.append({
                "type": "schema",
                "priority": "medium",
                "title": "Limited Table Relationships",
                "description": "Many tables lack foreign key relationships. This may affect query generation quality.",
                "action": "Consider adding foreign key constraints or business glossary terms"
            })
        
        # Check for complex data types
        complex_type_tables = []
        for table_name, table_info in self.schema_info.items():
            for col in table_info['columns']:
                col_type = str(col['type']).lower()
                if 'json' in col_type or 'xml' in col_type or 'array' in col_type:
                    complex_type_tables.append(table_name)
                    break
        
        if complex_type_tables:
            recommendations.append({
                "type": "compatibility",
                "priority": "medium",
                "title": "Complex Data Types Found",
                "description": f"Tables {', '.join(complex_type_tables[:3])} contain JSON/XML/Array columns.",
                "action": "May require custom query templates for complex data type handling"
            })
        
        return recommendations
    
    def export_analysis(self, filename: str = "schema_analysis.json"):
        """Export analysis results to JSON file"""
        try:
            with open(filename, 'w') as f:
                json.dump(self.analysis_results, f, indent=2, default=str)
            logger.info(f"Schema analysis exported to {filename}")
        except Exception as e:
            logger.error(f"Failed to export analysis: {str(e)}")
    
    def get_optimization_suggestions(self) -> List[str]:
        """Get specific optimization suggestions for GenBI"""
        suggestions = []
        
        if not self.analysis_results:
            return ["Run schema analysis first"]
        
        complexity = self.analysis_results.get('complexity_analysis', {})
        
        # High-dimensional table suggestions
        high_dim_tables = complexity.get('high_dimensional_tables', [])
        if high_dim_tables:
            suggestions.append(
                f"Consider creating focused views for high-dimensional tables: {', '.join(high_dim_tables[:3])}"
            )
        
        # Relationship suggestions
        relationships = self.analysis_results.get('relationship_analysis', {})
        if relationships.get('total_relationships', 0) < len(self.schema_info) * 0.5:
            suggestions.append(
                "Add business glossary terms to improve query understanding for tables with few relationships"
            )
        
        # Performance suggestions
        summary = self.analysis_results.get('summary', {})
        avg_columns = summary.get('avg_columns_per_table', 0)
        if avg_columns > 50:
            suggestions.append(
                "Enable semantic layer column filtering to improve query performance on wide tables"
            )
        
        return suggestions

def main():
    """CLI interface for schema analysis"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze database schema for GenBI optimization")
    parser.add_argument("--export", help="Export analysis to JSON file", default="schema_analysis.json")
    parser.add_argument("--connection", help="Database connection name", default="default")
    
    args = parser.parse_args()
    
    analyzer = SchemaAnalyzer()
    
    print("🔍 Analyzing database schema...")
    analysis = analyzer.analyze_database_schema(args.connection)
    
    if "error" in analysis:
        print(f"❌ Analysis failed: {analysis['error']}")
        return
    
    # Print summary
    summary = analysis['summary']
    print(f"\n📊 Schema Summary:")
    print(f"  Tables: {summary['total_tables']}")
    print(f"  Columns: {summary['total_columns']}")
    print(f"  Avg columns per table: {summary['avg_columns_per_table']:.1f}")
    
    # Print recommendations
    recommendations = analysis['recommendations']
    if recommendations:
        print(f"\n💡 Recommendations:")
        for rec in recommendations:
            print(f"  [{rec['priority'].upper()}] {rec['title']}")
            print(f"    {rec['description']}")
    
    # Export analysis
    if args.export:
        analyzer.export_analysis(args.export)
        print(f"\n📄 Analysis exported to {args.export}")

if __name__ == "__main__":
    main()
