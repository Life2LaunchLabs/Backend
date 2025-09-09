import re
import hashlib
from typing import Dict, List, Any


def generate_agenda_hash(agenda_content: str) -> str:
    """Generate a hash for agenda content to track versions"""
    if not agenda_content:
        return ""
    return hashlib.sha256(agenda_content.encode('utf-8')).hexdigest()


def parse_agenda_items(agenda_content: str) -> Dict[str, Any]:
    """
    Parse course agenda markdown into structured JSON format.
    
    Args:
        agenda_content: Markdown content of the course agenda
        
    Returns:
        Dict containing parsed agenda structure with items list
    """
    if not agenda_content:
        return {"about": "", "items": []}
    
    lines = agenda_content.split('\n')
    result = {
        "about": "",
        "items": []
    }
    
    current_section = None
    about_lines = []
    
    for line in lines:
        line = line.strip()
        
        # Skip empty lines
        if not line:
            continue
            
        # Parse main sections - be specific about header levels
        if line.startswith('## About'):
            current_section = 'about'
            continue
        elif line.startswith('## Items'):
            current_section = 'items'
            continue
        elif line.startswith('##') and not line.startswith('###'):
            # Other level 2 headers, skip
            current_section = None
            continue
        elif line.startswith('# ') and not line.startswith('##'):
            # Level 1 headers, skip
            current_section = None
            continue
            
        # Process content based on current section
        if current_section == 'about':
            if line and not line.startswith('#'):
                about_lines.append(line)
        elif current_section == 'items':
            # Parse question items that match "### N. Title"
            match = re.match(r'^### (\d+)\. (.+)$', line)
            if match:
                number = int(match.group(1))
                title = match.group(2)
                
                # Generate question ID from title
                question_id = generate_question_id(title)
                
                result["items"].append({
                    "number": number,
                    "title": title,
                    "question_id": question_id,
                    "description": ""  # Could be enhanced to capture following lines
                })
    
    # Join about lines
    result["about"] = '\n'.join(about_lines).strip()
    
    # Sort items by number to ensure correct order
    result["items"].sort(key=lambda x: x['number'])
    
    return result


def generate_question_id(title: str) -> str:
    """
    Generate a stable question ID from the title.
    
    Args:
        title: Question title from agenda
        
    Returns:
        Lowercase, underscore-separated question ID
    """
    # Convert to lowercase and replace spaces/special chars with underscores
    question_id = re.sub(r'[^a-zA-Z0-9\s]', '', title.lower())
    question_id = re.sub(r'\s+', '_', question_id)
    question_id = question_id.strip('_')
    
    return question_id


def extract_question_details(agenda_content: str, question_number: int) -> Dict[str, Any]:
    """
    Extract detailed information for a specific question from the agenda.
    
    Args:
        agenda_content: Full agenda markdown content
        question_number: The question number to extract (1-based)
        
    Returns:
        Dict with question details including text, type, etc.
    """
    if not agenda_content:
        return {}
    
    lines = agenda_content.split('\n')
    in_items_section = False
    current_question = None
    question_lines = []
    
    for line in lines:
        line_stripped = line.strip()
        
        if line_stripped.startswith('## Items'):
            in_items_section = True
            continue
        elif line_stripped.startswith('##') and in_items_section:
            # End of items section
            break
            
        if in_items_section:
            # Check if this is a question header
            match = re.match(r'^### (\d+)\. (.+)$', line_stripped)
            if match:
                # If we were processing a question and this is a new one
                if current_question and current_question['number'] == question_number:
                    break  # We found our question, exit
                    
                current_question = {
                    'number': int(match.group(1)),
                    'title': match.group(2),
                    'question_id': generate_question_id(match.group(2))
                }
                question_lines = []
            elif current_question and line_stripped:
                # Collect lines for the current question
                question_lines.append(line_stripped)
    
    # If we found the question we were looking for
    if current_question and current_question['number'] == question_number:
        current_question['description'] = '\n'.join(question_lines)
        
        # Try to extract question type from description
        description_lower = current_question['description'].lower()
        if '(short answer)' in description_lower:
            current_question['response_type'] = 'short_answer'
        elif '(long answer)' in description_lower:
            current_question['response_type'] = 'long_answer'
        elif '(multiple choice)' in description_lower:
            current_question['response_type'] = 'multiple_choice'
        else:
            current_question['response_type'] = 'text'
            
        return current_question
    
    return {}


def validate_agenda_format(agenda_content: str) -> Dict[str, Any]:
    """
    Validate that the agenda content follows the expected format.
    
    Args:
        agenda_content: Markdown agenda content to validate
        
    Returns:
        Dict with validation results and any issues found
    """
    if not agenda_content:
        return {"valid": False, "issues": ["Empty agenda content"]}
    
    issues = []
    parsed = parse_agenda_items(agenda_content)
    
    # Check if we have any items
    if not parsed["items"]:
        issues.append("No question items found")
    
    # Check for sequential numbering
    numbers = [item["number"] for item in parsed["items"]]
    if numbers != list(range(1, len(numbers) + 1)):
        issues.append("Question numbers are not sequential starting from 1")
    
    # Check for duplicate question IDs
    question_ids = [item["question_id"] for item in parsed["items"]]
    if len(question_ids) != len(set(question_ids)):
        issues.append("Duplicate question IDs found")
    
    # Check basic structure
    lines = agenda_content.split('\n')
    has_about = any('## About' in line for line in lines)
    has_items = any('## Items' in line for line in lines)
    
    if not has_about:
        issues.append("Missing '## About' section")
    if not has_items:
        issues.append("Missing '## Items' section")
    
    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "item_count": len(parsed["items"]),
        "parsed": parsed
    }