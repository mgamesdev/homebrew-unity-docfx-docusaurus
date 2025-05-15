#!/usr/bin/env python3
import os
import re
import time
import yaml
import logging
import asyncio
import shutil
import inspect
import functools
from typing import List, Dict, Optional, Any, Callable
from pathlib import Path
from dataclasses import dataclass, field

# Configure enhanced logging
# Define custom log levels
TRACE = 5
logging.addLevelName(TRACE, "TRACE")
DETAIL = 15
logging.addLevelName(DETAIL, "DETAIL")

class EnhancedLogger(logging.Logger):
    def trace(self, msg, *args, **kwargs):
        """Detailed tracing information (more verbose than debug)"""
        if self.isEnabledFor(TRACE):
            self._log(TRACE, msg, args, **kwargs)
            
    def detail(self, msg, *args, **kwargs):
        """Detailed information (between DEBUG and INFO)"""
        if self.isEnabledFor(DETAIL):
            self._log(DETAIL, msg, args, **kwargs)

# Set up custom logger
logging.setLoggerClass(EnhancedLogger)
logger = logging.getLogger("DocFxMarkdownGen")

# Create console handler with better formatting
console_handler = logging.StreamHandler()
log_format = '%(levelname)-7s [%(filename)s:%(lineno)d] %(message)s'
console_handler.setFormatter(logging.Formatter(log_format))
logger.addHandler(console_handler)
logger.setLevel(logging.INFO)

# Add file handler for persistent debugging
file_handler = logging.FileHandler("docfx_markdown_gen.log", mode='w')
file_format = '%(asctime)s - %(levelname)-7s [%(filename)s:%(lineno)d] %(message)s'
file_handler.setFormatter(logging.Formatter(file_format))
file_handler.setLevel(TRACE)  # Log everything to file
logger.addHandler(file_handler)

# Set DEBUG level if environment variable is set
if os.environ.get("JAN_DEBUG") == "1":
    logger.setLevel(logging.DEBUG)
    logger.debug("Debug logging enabled via JAN_DEBUG environment variable")
    
# Create a function decorator for logging function entry/exit
def log_func(level=logging.DEBUG):
    """Decorator to log function entry and exit with timing"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_name = func.__name__
            arg_info = ""
            if args and hasattr(args[0], "__class__"):
                arg_info = f" - first arg: {args[0].__class__.__name__}"
            
            logger.log(level, f"ENTER: {func_name}{arg_info}")
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                elapsed = (time.time() - start_time) * 1000
                logger.log(level, f"EXIT: {func_name} - took {elapsed:.2f}ms")
                return result
            except Exception as e:
                logger.error(f"EXCEPTION in {func_name}: {str(e)}")
                raise
        
        return wrapper
    return decorator

# Context manager for timing blocks of code
class LogTimer:
    def __init__(self, name, level=logging.INFO):
        self.name = name
        self.level = level
        self.start_time = None
        
    def __enter__(self):
        self.start_time = time.time()
        logger.log(self.level, f"⏱️ START: {self.name}")
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        elapsed = (time.time() - self.start_time) * 1000
        if exc_type:
            logger.error(f"⏱️ FAILED: {self.name} after {elapsed:.2f}ms - {exc_val}")
        else:
            logger.log(self.level, f"⏱️ COMPLETE: {self.name} - {elapsed:.2f}ms")

# Get version - simplified for conversion
version_string = "1.0.0"
print(f"DocFxMarkdownGen v{version_string} running...")

# Compile regular expressions
xref_regex = re.compile(r'<xref href="(.+?)" data-throw-if-not-resolved="false"></xref>')
langword_xref_regex = re.compile(r'<xref uid="langword_csharp_.+?" name="(.+?)" href=""></xref>')
code_block_regex = re.compile(r'<pre><code class="lang-csharp">((.|\n)+?)</code></pre>')
code_regex = re.compile(r'<code>(.+?)</code>')
link_regex = re.compile(r'<a href="(.+?)">(.+?)</a>')
br_regex = re.compile(r'<br */?>') 

# Define data classes for YAML structure
@dataclass
class Remote:
    path: str
    branch: str
    repo: str

@dataclass
class Source:
    remote: Optional[Remote] = None
    id: str = ""
    path: str = ""
    start_line: int = 0

@dataclass
class Parameter:
    id: str
    type: str
    description: Optional[str] = None

@dataclass
class TypeParameter:
    id: str
    description: str = ""

@dataclass
class SyntaxReturn:
    type: str
    description: Optional[str] = None

@dataclass
class Syntax:
    content: str = ""
    content_vb: str = ""
    parameters: Optional[List[Parameter]] = None
    type_parameters: Optional[List[TypeParameter]] = None
    return_value: Optional[SyntaxReturn] = None

@dataclass
class ThrowsException:
    type: str
    comment_id: str
    description: str

@dataclass
class Item:
    uid: str = ""
    comment_id: str = ""
    id: str = ""
    parent: str = ""
    children: List[str] = field(default_factory=list)
    langs: List[str] = field(default_factory=list)
    definition: str = ""
    name: str = ""
    name_with_type: str = ""
    full_name: str = ""
    type: str = ""
    source: Optional[Source] = None
    assemblies: List[str] = field(default_factory=list)
    namespace: str = ""
    summary: Optional[str] = None
    syntax: Optional[Syntax] = None
    inheritance: Optional[List[str]] = None
    derived_classes: Optional[List[str]] = None
    implements: Optional[List[str]] = None
    extension_methods: Optional[List[str]] = None
    exceptions: Optional[List[ThrowsException]] = None

@dataclass
class DocFxFile:
    items: List[Item]

@dataclass
class ConfigTypesGrouping:
    enabled: bool
    min_count: int = 12

@dataclass
class Config:
    yaml_path: str = "./Documentation~/api"
    output_path: str = "./docusaroaus"
    index_slug: str = "/api"
    types_grouping: Optional[ConfigTypesGrouping] = None
    br_newline: str = "\n\n"
    force_newline: bool = False
    forced_newline: str = "  \n"
    rewrite_interlinks: bool = False

# Utility functions
def get_type_path_part(type_name):
    """Convert type name to directory name"""
    type_map = {
        "Class": "Classes",
        "Struct": "Structs",
        "Interface": "Interfaces",
        "Enum": "Enums",
        "Delegate": "Delegates"
    }
    
    if type_name not in type_map:
        raise ValueError(f"Unknown type: {type_name}")
    
    return type_map[type_name]

def html_escape(text):
    """Escape HTML special characters"""
    if text is None:
        return None
    return text.replace("<", "&lt;").replace(">", "&gt;")

def file_escape(text):
    """Escape characters in file paths"""
    if text is None:
        return None
    return text.replace("<", "`").replace(">", "`").replace(" ", "%20")

def source_link(item):
    """Generate source code link"""
    if item.source is None or item.source.remote is None:
        return ""
    return f"###### [View Source]({item.source.remote.repo}/blob/{item.source.remote.branch}/{item.source.remote.path}#L{item.source.start_line + 1})"

def get_properties(items, uid):
    """Get properties for a type"""
    return [i for i in items if i.parent == uid and i.type == "Property"]

def get_fields(items, uid):
    """Get fields for a type"""
    return [i for i in items if i.parent == uid and i.type == "Field"]

def get_methods(items, uid):
    """Get methods for a type"""
    return [i for i in items if i.parent == uid and i.type == "Method"]

def get_events(items, uid):
    """Get events for a type"""
    return [i for i in items if i.parent == uid and i.type == "Event"]

def declaration(str_builder, item):
    """Add declaration to string builder"""
    str_builder.append(source_link(item) + "\n")
    if item.syntax and hasattr(item.syntax, 'content') and item.syntax.content:
        str_builder.append("```csharp title=\"Declaration\"\n")
        str_builder.append(item.syntax.content + "\n")
        str_builder.append("```\n")

@log_func()
def load_config():
    """Load configuration from YAML file"""
    config_path = os.environ.get("DFMG_CONFIG", "./config.yaml")
    logger.info(f"Loading configuration from: {config_path}")
    
    try:
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        logger.detail(f"Raw config data keys: {list(config_data.keys())}")
    except Exception as e:
        logger.error(f"Failed to load config file {config_path}: {e}")
        raise
    
    types_grouping = None
    if 'typesGrouping' in config_data:
        types_grouping = ConfigTypesGrouping(
            enabled=config_data['typesGrouping'].get('enabled', False),
            min_count=config_data['typesGrouping'].get('minCount', 12)
        )
        logger.debug(f"Type grouping enabled: {types_grouping.enabled}, min_count: {types_grouping.min_count}")
    
    config = Config(
        yaml_path=config_data['yamlPath'],
        output_path=config_data['outputPath'],
        index_slug=config_data.get('indexSlug', '/api'),
        types_grouping=types_grouping,
        br_newline=config_data.get('brNewline', '\n\n'),
        force_newline=config_data.get('forceNewline', False),
        forced_newline=config_data.get('forcedNewline', '  \n'),
        rewrite_interlinks=config_data.get('rewriteInterlinks', False)
    )
    
    # Override from environment variables
    if os.environ.get("DFMG_OUTPUT_PATH"):
        old_path = config.output_path
        config.output_path = os.environ.get("DFMG_OUTPUT_PATH")
        logger.info(f"Output path overridden by env: {old_path} → {config.output_path}")
    
    if os.environ.get("DFMG_YAML_PATH"):
        old_path = config.yaml_path
        config.yaml_path = os.environ.get("DFMG_YAML_PATH")
        logger.info(f"YAML path overridden by env: {old_path} → {config.yaml_path}")
    
    logger.debug(f"Final configuration: yaml_path={config.yaml_path}, output_path={config.output_path}")
    return config

@log_func(level=logging.DEBUG)
def namespace_has_type_grouping(namespace, type_counts, config):
    """Check if namespace has type grouping enabled"""
    if not config.types_grouping or not config.types_grouping.enabled:
        logger.trace(f"Type grouping disabled for namespace {namespace}")
        return False
    
    has_grouping = namespace in type_counts and type_counts[namespace] >= config.types_grouping.min_count
    
    if has_grouping:
        logger.debug(f"Namespace {namespace} has type grouping enabled with {type_counts[namespace]} types")
    else:
        logger.trace(f"Namespace {namespace} has type grouping disabled, count: {type_counts.get(namespace, 0)}")
    
    return has_grouping

@log_func(level=logging.DEBUG)
def process_summary(summary, link_from_grouped_type, config, items, namespace_has_type_grouping_func):
    """Process summary text, replacing special markup"""
    if summary is None:
        return None
    
    original_length = len(summary)
    transformations = []
    
    def link_replacer(match):
        uid = match.group(1)
        return create_link(uid, link_from_grouped_type, items, namespace_has_type_grouping_func, config)
    
    # Apply all regex transformations and track them
    if xref_regex.search(summary):
        summary = xref_regex.sub(link_replacer, summary)
        transformations.append("xref_links")
    
    if langword_xref_regex.search(summary):
        summary = langword_xref_regex.sub(lambda m: f"`{m.group(1)}`", summary)
        transformations.append("langword_xrefs")
    
    if code_block_regex.search(summary):
        summary = code_block_regex.sub(lambda m: f"```csharp\n{m.group(1).strip()}\n```", summary)
        transformations.append("code_blocks")
    
    if code_regex.search(summary):
        summary = code_regex.sub(lambda m: f"`{m.group(1)}`", summary)
        transformations.append("inline_code")
    
    if link_regex.search(summary):
        summary = link_regex.sub(lambda m: f"[{m.group(2)}]({m.group(1)})", summary)
        transformations.append("links")
    
    if br_regex.search(summary):
        summary = br_regex.sub(lambda _: config.br_newline, summary)
        transformations.append("line_breaks")
    
    if config.force_newline and "\n" in summary:
        summary = summary.replace("\n", config.forced_newline)
        transformations.append("force_newline")
    
    # Only log if transformations were made
    if transformations:
        new_length = len(summary)
        logger.debug(f"Summary processed: {', '.join(transformations)} ({original_length} → {new_length} chars)")
        
    return html_escape(summary)

@log_func(level=logging.DEBUG)
def create_link(uid, link_from_grouped_type, items, namespace_has_type_grouping_func, config, name_only=False, link_from_index=False):
    """Create a link to another item"""
    # Find the reference by UID
    reference = next((i for i in items if i.uid == uid), None)
    
    # Try to resolve single type argument references
    if '{' in uid and reference is None:
        start_idx = uid.find('{')
        end_idx = uid.rfind('}')
        if start_idx != -1 and end_idx != -1:
            replaced = uid[:start_idx] + "`1" + uid[end_idx+1:]
            reference = next((i for i in items if i.uid == replaced), None)
            
            if reference:
                logger.detail(f"Resolved generic type argument reference: {uid} → {replaced}")
    
    # If we can't find a reference, return a code block
    if reference is None:
        logger.detail(f"Unable to resolve link for UID: {uid}")
        return f"`{uid.replace('{', '<').replace('}', '>')}`"
    
    # Determine name and path construction elements
    name = reference.name if name_only else reference.full_name
    dots = "./" if link_from_index else "../../" if link_from_grouped_type else "../"
    extension = ".md" if link_from_index else ""
    
    # Build the appropriate link based on the reference type
    if reference.type in ["Class", "Interface", "Enum", "Struct", "Delegate"]:
        has_grouping = namespace_has_type_grouping_func(reference.namespace)
        
        if has_grouping:
            link = f"[{html_escape(name)}]({file_escape(f'{dots}{reference.namespace}/{get_type_path_part(reference.type)}/{reference.name}{extension}')})"
            logger.trace(f"Created grouped type link for {reference.type} {reference.name}")
            return link
        else:
            link = f"[{html_escape(name)}]({file_escape(f'{dots}{reference.namespace}/{reference.name}{extension}')})"
            logger.trace(f"Created type link for {reference.type} {reference.name}")
            return link
            
    elif reference.type == "Namespace":
        if config.rewrite_interlinks:
            if link_from_index:
                link = f"[{html_escape(name)}]({file_escape(f'{dots}{reference.name}/{reference.name}{extension}')})"
                logger.trace(f"Created rewritten namespace link from index for {reference.name}")
                return link
            else:
                link = f"[{html_escape(name)}]({file_escape(f'{dots}{reference.name}')})"
                logger.trace(f"Created rewritten namespace link for {reference.name}")
                return link
        
        link = f"[{html_escape(name)}]({file_escape(f'{dots}{reference.name}/{reference.name}{extension}')})"
        logger.trace(f"Created namespace link for {reference.name}")
        return link
        
    else:
        # For members, we need to find the parent
        parent = next((i for i in items if i.uid == reference.parent), None)
        if parent is None:
            logger.detail(f"Unable to find parent for {reference.type} {reference.name} with UID: {reference.parent}")
            return f"`{uid.replace('{', '<').replace('}', '>')}`"
        
        # Create anchor link
        anchor = reference.name.lower().replace("(", "").replace(")", "").replace("?", "")
        path_part = f"/{get_type_path_part(parent.type)}" if namespace_has_type_grouping_func(parent.namespace) else ""
        
        link = f"[{html_escape(name)}]({file_escape(f'{dots}{reference.namespace}{path_part}/{parent.name}{extension}')}#{anchor})"
        logger.trace(f"Created member link for {reference.type} {reference.name}")
        return link

@log_func(level=logging.INFO)
async def read_yaml_files(config, items):
    """Read all YAML files in parallel"""
    with LogTimer("Reading all YAML files", level=logging.INFO):
        yaml_files = [f for f in os.listdir(config.yaml_path) if f.endswith(".yml") and f != "toc.yml"]
        logger.info(f"Found {len(yaml_files)} YAML files to process in {config.yaml_path}")
        
        type_counts = {"Namespace": 0, "Class": 0, "Interface": 0, "Enum": 0, 
                      "Struct": 0, "Delegate": 0, "Method": 0, "Property": 0, 
                      "Field": 0, "Event": 0, "Other": 0}
        
        @log_func(level=logging.DEBUG)
        async def process_file(file):
            file_path = os.path.join(config.yaml_path, file)
            logger.debug(f"Processing YAML file: {file_path}")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    yaml_content = yaml.safe_load(f)
                    
                if not yaml_content or 'items' not in yaml_content:
                    logger.warning(f"No items found in {file_path}")
                    return []
                
                local_type_counts = {}
                file_items = []
                for item_data in yaml_content.get('items', []):
                    item_type = item_data.get('type', 'Unknown')
                    
                    # Count item types
                    if item_type not in local_type_counts:
                        local_type_counts[item_type] = 0
                    local_type_counts[item_type] += 1
                    
                    # Process syntax if present
                    if 'syntax' in item_data:
                        syntax_data = item_data['syntax']
                        syntax = Syntax(
                            content=syntax_data.get('content', ''),
                            content_vb=syntax_data.get('content.vb', '')
                        )
                        
                        # Process parameters
                        if 'parameters' in syntax_data:
                            syntax.parameters = []
                            logger.trace(f"Processing {len(syntax_data['parameters'])} parameters for {item_data.get('name', 'unnamed')}")
                            for param in syntax_data['parameters']:
                                syntax.parameters.append(Parameter(
                                    id=param.get('id', ''),
                                    type=param.get('type', ''),
                                    description=param.get('description')
                                ))
                        
                        # Process type parameters
                        if 'typeParameters' in syntax_data:
                            syntax.type_parameters = []
                            for tp in syntax_data['typeParameters']:
                                syntax.type_parameters.append(TypeParameter(
                                    id=tp.get('id', ''),
                                    description=tp.get('description', '')
                                ))
                        
                        # Process return
                        if 'return' in syntax_data:
                            ret = syntax_data['return']
                            syntax.return_value = SyntaxReturn(
                                type=ret.get('type', ''),
                                description=ret.get('description')
                            )
                        
                        item_data['syntax'] = syntax
                    
                    # Process source if present
                    if 'source' in item_data and item_data['source']:
                        source_data = item_data['source']
                        remote = None
                        if 'remote' in source_data and source_data['remote']:
                            remote_data = source_data['remote']
                            remote = Remote(
                                path=remote_data.get('path', ''),
                                branch=remote_data.get('branch', ''),
                                repo=remote_data.get('repo', '')
                            )
                        
                        item_data['source'] = Source(
                            remote=remote,
                            id=source_data.get('id', ''),
                            path=source_data.get('path', ''),
                            start_line=source_data.get('startLine', 0)
                        )
                    
                    # Process exceptions if present
                    if 'exceptions' in item_data and item_data['exceptions']:
                        exceptions = []
                        for exc in item_data['exceptions']:
                            exceptions.append(ThrowsException(
                                type=exc.get('type', ''),
                                comment_id=exc.get('commentId', ''),
                                description=exc.get('description', '')
                            ))
                        item_data['exceptions'] = exceptions
                    
                    # Create item
                    item = Item(
                        uid=item_data.get('uid', ''),
                        comment_id=item_data.get('commentId', ''),
                        id=item_data.get('id', ''),
                        parent=item_data.get('parent', ''),
                        children=item_data.get('children', []),
                        langs=item_data.get('langs', []),
                        definition=item_data.get('definition', ''),
                        name=item_data.get('name', ''),
                        name_with_type=item_data.get('nameWithType', ''),
                        full_name=item_data.get('fullName', ''),
                        type=item_data.get('type', ''),
                        source=item_data.get('source'),
                        assemblies=item_data.get('assemblies', []),
                        namespace=item_data.get('namespace', ''),
                        summary=item_data.get('summary'),
                        syntax=item_data.get('syntax'),
                        inheritance=item_data.get('inheritance'),
                        derived_classes=item_data.get('derivedClasses'),
                        implements=item_data.get('implements'),
                        extension_methods=item_data.get('extensionMethods'),
                        exceptions=item_data.get('exceptions')
                    )
                    file_items.append(item)
                
                logger.debug(f"File {file} contains items: {local_type_counts}")
                return file_items
            
            except Exception as e:
                logger.error(f"Error processing file {file_path}: {e}", exc_info=True)
                raise
        
        # Process all files in parallel
        tasks = [process_file(file) for file in yaml_files]
        results = await asyncio.gather(*tasks)
        
        total_items = 0
        for file_items in results:
            items.extend(file_items)
            total_items += len(file_items)
            
            # Count item types for statistics
            for item in file_items:
                if item.type in type_counts:
                    type_counts[item.type] += 1
                else:
                    type_counts["Other"] += 1
        
        # Log item type statistics
        logger.info(f"Processed {total_items} total items from {len(yaml_files)} files")
        type_info = ", ".join([f"{k}: {v}" for k, v in type_counts.items() if v > 0])
        logger.info(f"Item type statistics: {type_info}")
        
        return items

@log_func()
def create_namespace_directories(config, items):
    """Create directories for namespaces"""
    logger.info(f"Creating namespace directories in {config.output_path}")
    namespace_count = 0
    
    for item in items:
        if item.type == "Namespace":
            namespace_count += 1
            dir_path = os.path.join(config.output_path, item.name)
            logger.debug(f"Creating directory for namespace: {item.name}")
            os.makedirs(dir_path, exist_ok=True)
    
    logger.info(f"Created {namespace_count} namespace directories")

@log_func()
def count_types(items):
    """Count types in each namespace for grouping decisions"""
    type_counts = {}
    namespace_type_details = {}
    
    for item in items:
        if item.type in ["Class", "Interface", "Enum", "Struct", "Delegate"]:
            # Update the count for this namespace
            if item.namespace in type_counts:
                type_counts[item.namespace] += 1
            else:
                type_counts[item.namespace] = 1
                namespace_type_details[item.namespace] = {
                    "Class": 0, "Interface": 0, "Enum": 0, "Struct": 0, "Delegate": 0
                }
            
            # Track details for debugging
            if item.namespace in namespace_type_details:
                namespace_type_details[item.namespace][item.type] += 1
    
    # Log detailed type counts by namespace
    logger.info(f"Found {len(type_counts)} namespaces with types")
    
    # Log details for each namespace
    for namespace, count in sorted(type_counts.items(), key=lambda x: x[1], reverse=True):
        if count > 5:  # Only log details for namespaces with a significant number of types
            details = namespace_type_details.get(namespace, {})
            detail_str = ", ".join([f"{k}: {v}" for k, v in details.items() if v > 0])
            logger.debug(f"Namespace {namespace}: {count} types ({detail_str})")
    
    return type_counts

async def generate_type_markdown(config, item, items, type_counts):
    """Generate markdown for a type (class, interface, etc.)"""
    is_grouped_type = (config.types_grouping and 
                      config.types_grouping.enabled and 
                      item.namespace in type_counts and 
                      type_counts[item.namespace] >= config.types_grouping.min_count)
    
    # Create a function for namespace_has_type_grouping
    def nht_func(namespace):
        return namespace_has_type_grouping(namespace, type_counts, config)
    
    str_builder = []
    str_builder.append("---\n")
    str_builder.append(f"title: {item.type} {item.name}\n")
    str_builder.append(f"sidebar_label: {item.name}\n")
    
    if item.summary:
        summary = process_summary(item.summary, is_grouped_type, config, items, nht_func)
        if summary:
            escaped_summary = summary.strip().replace('"', '\\"')
            str_builder.append(f'description: "{escaped_summary}"\n')
    
    str_builder.append("---\n")
    str_builder.append(f"# {item.type} {html_escape(item.name)}\n")
    
    summary = process_summary(item.summary, is_grouped_type, config, items, nht_func)
    if summary:
        str_builder.append(f"{summary.strip()}\n\n")
    
    if item.assemblies and len(item.assemblies) > 0:
        str_builder.append(f"###### **Assembly**: {item.assemblies[0]}.dll\n")
    declaration(str_builder, item)
    
    # Inheritance hierarchy
    if item.inheritance and len(item.inheritance) > 1:
        str_builder.append("**Inheritance:** ")
        for i, inheritance_item in enumerate(item.inheritance):
            str_builder.append(create_link(inheritance_item, is_grouped_type, items, nht_func, config))
            if i != len(item.inheritance) - 1:
                str_builder.append(" -> ")
        str_builder.append("\n\n")
    
    # Derived classes
    if item.derived_classes:
        str_builder.append("**Derived:**  \n")
        if len(item.derived_classes) > 8:
            str_builder.append("\n<details>\n<summary>Expand</summary>\n\n")
        
        for i, derived_class in enumerate(item.derived_classes):
            str_builder.append(create_link(derived_class, is_grouped_type, items, nht_func, config))
            if i != len(item.derived_classes) - 1:
                str_builder.append(", ")
        
        if len(item.derived_classes) > 8:
            str_builder.append("\n</details>\n")
        str_builder.append("\n\n")
    
    # Implements
    if item.implements:
        str_builder.append("**Implements:**  \n")
        if len(item.implements) > 8:
            str_builder.append("\n<details>\n<summary>Expand</summary>\n\n")
        
        for i, impl in enumerate(item.implements):
            str_builder.append(create_link(impl, is_grouped_type, items, nht_func, config))
            if i != len(item.implements) - 1:
                str_builder.append(", ")
        
        if len(item.implements) > 8:
            str_builder.append("\n</details>\n")
        str_builder.append("\n\n")
    
    # Properties
    properties = get_properties(items, item.uid)
    if properties:
        str_builder.append("## Properties\n")
        for prop in properties:
            str_builder.append(f"### {prop.name}\n")
            summary = process_summary(prop.summary, is_grouped_type, config, items, nht_func)
            if summary:
                str_builder.append(f"{summary.strip()}\n")
            declaration(str_builder, prop)
    
    # Fields
    fields = get_fields(items, item.uid)
    if fields:
        str_builder.append("## Fields\n")
        for field in fields:
            str_builder.append(f"### {field.name}\n")
            summary = process_summary(field.summary, is_grouped_type, config, items, nht_func)
            if summary:
                str_builder.append(f"{summary.strip()}\n")
            declaration(str_builder, field)
    
    # Methods
    methods = get_methods(items, item.uid)
    if methods:
        str_builder.append("## Methods\n")
        for method in methods:
            str_builder.append(f"### {html_escape(method.name)}\n")
            summary = process_summary(method.summary, is_grouped_type, config, items, nht_func)
            if summary:
                str_builder.append(f"{summary.strip()}\n")
            declaration(str_builder, method)
            
            if method.syntax and method.syntax.return_value and method.syntax.return_value.type:
                str_builder.append("\n##### Returns\n\n")
                str_builder.append(create_link(method.syntax.return_value.type, is_grouped_type, items, nht_func, config).strip())
                
                if not method.syntax.return_value.description:
                    str_builder.append("\n")
                else:
                    str_builder.append(": " + process_summary(method.syntax.return_value.description, is_grouped_type, config, items, nht_func))
            
            if method.syntax and method.syntax.parameters:
                str_builder.append("\n##### Parameters\n\n")
                
                if any(p.description for p in method.syntax.parameters):
                    str_builder.append("| Type | Name | Description |\n")
                    str_builder.append("|:--- |:--- |:--- |\n")
                    for param in method.syntax.parameters:
                        param_type = create_link(param.type, is_grouped_type, items, nht_func, config)
                        param_desc = process_summary(param.description, is_grouped_type, config, items, nht_func) or ""
                        str_builder.append(f"| {param_type} | *{param.id}* | {param_desc} |\n")
                else:
                    str_builder.append("| Type | Name |\n")
                    str_builder.append("|:--- |:--- |\n")
                    for param in method.syntax.parameters:
                        param_type = create_link(param.type, is_grouped_type, items, nht_func, config)
                        str_builder.append(f"| {param_type} | *{param.id}* |\n")
                
                str_builder.append("\n")
            
            if method.syntax and method.syntax.type_parameters:
                str_builder.append("##### Type Parameters\n")
                
                if any(tp.description for tp in method.syntax.type_parameters):
                    str_builder.append("| Name | Description |\n")
                    str_builder.append("|:--- |:--- |\n")
                    for type_param in method.syntax.type_parameters:
                        str_builder.append(f"| {create_link(type_param.id, is_grouped_type, items, nht_func, config)} | {type_param.description} |\n")
                else:
                    for type_param in method.syntax.type_parameters:
                        str_builder.append(f"* {create_link(type_param.id, is_grouped_type, items, nht_func, config)}\n")
            
            if method.exceptions:
                str_builder.append("\n##### Exceptions\n\n")
                for exception in method.exceptions:
                    str_builder.append(f"{create_link(exception.type, is_grouped_type, items, nht_func, config)}  \n")
                    summary = process_summary(exception.description, is_grouped_type, config, items, nht_func)
                    if summary:
                        str_builder.append(f"{summary.strip()}\n")
    
    # Events
    events = get_events(items, item.uid)
    if events:
        str_builder.append("## Events\n")
        for event in events:
            str_builder.append(f"### {html_escape(event.name)}\n")
            summary = process_summary(event.summary, is_grouped_type, config, items, nht_func)
            if summary:
                str_builder.append(f"{summary.strip()}\n")
            declaration(str_builder, event)
            
            if event.syntax and event.syntax.return_value:
                str_builder.append("##### Event Type\n")
                event_link = create_link(event.syntax.return_value.type, is_grouped_type, items, nht_func, config).strip()
                if not event.syntax.return_value.description:
                    str_builder.append(f"{event_link}\n")
                else:
                    str_builder.append(f"{event_link}: {event.syntax.return_value.description}\n")
    
    # Implements section
    if item.implements:
        str_builder.append("\n## Implements\n\n")
        for impl in item.implements:
            str_builder.append(f"* {create_link(impl, is_grouped_type, items, nht_func, config)}\n")
    
    # Extension methods
    if item.extension_methods and len(item.extension_methods) > 1:
        str_builder.append("## Extension Methods\n")
        for ext_method in item.extension_methods:
            method = None
            for i in items:
                if (i.syntax and i.syntax.parameters and i.syntax.parameters[0].type + '.' + 
                    i.full_name[:i.full_name.find('(') if '(' in i.full_name else len(i.full_name)] == ext_method):
                    method = i
                    break
            
            if method is None:
                str_builder.append(f"* {ext_method.replace('{', '&#123;').replace('}', '&#125;')}\n")
            else:
                str_builder.append(f"* {create_link(method.uid, is_grouped_type, items, nht_func, config)}\n")
    
    # Determine output path
    if is_grouped_type:
        path = os.path.join(
            config.output_path, 
            item.namespace, 
            get_type_path_part(item.type),
            item.name.replace('<', '`').replace('>', '`') + ".md"
        )
    else:
        path = os.path.join(
            config.output_path, 
            item.namespace, 
            item.name.replace('<', '`').replace('>', '`') + ".md"
        )
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(path), exist_ok=True)
    
    # Write the file
    with open(path, 'w', encoding='utf-8') as f:
        f.write("".join(str_builder))

async def generate_namespace_markdown(config, item, items):
    """Generate markdown for a namespace"""
    str_builder = []
    str_builder.append("---\n")
    str_builder.append(f"title: {item.type} {item.name}\n")
    str_builder.append(f"sidebar_label: {item.name}\n")
    str_builder.append("---\n")
    str_builder.append(f"# Namespace {html_escape(item.name)}\n")
    
    def add_type_section(type_name, header):
        type_items = [i for i in items if i.namespace == item.name and i.type == type_name]
        if type_items:
            str_builder.append(f"## {header}\n")
            for type_item in sorted(type_items, key=lambda i: i.name):
                str_builder.append(f"### {html_escape(create_link(type_item.uid, False, items, lambda _: False, config, name_only=True))}\n")
                summary = process_summary(type_item.summary, False, config, items, lambda _: False)
                if summary:
                    str_builder.append(f"{summary.strip()}\n")
    
    add_type_section("Class", "Classes")
    add_type_section("Struct", "Structs")
    add_type_section("Interface", "Interfaces")
    add_type_section("Enum", "Enums")
    add_type_section("Delegate", "Delegates")
    
    path = os.path.join(config.output_path, item.name, f"{item.name}.md")
    with open(path, 'w', encoding='utf-8') as f:
        f.write("".join(str_builder))

async def generate_index_markdown(config, items):
    """Generate the index markdown file"""
    str_builder = []
    str_builder.append("---\n")
    str_builder.append("title: Index\n")
    str_builder.append("sidebar_label: Index\n")
    str_builder.append("sidebar_position: 0\n")
    str_builder.append(f"slug: {config.index_slug}\n")
    str_builder.append("---\n")
    str_builder.append("# API Index\n")
    str_builder.append("## Namespaces\n")
    
    for namespace in sorted([i for i in items if i.type == "Namespace"], key=lambda i: i.name):
        str_builder.append(f"* {html_escape(create_link(namespace.uid, False, items, lambda _: False, config, name_only=False, link_from_index=True))}\n")
    
    str_builder.append("\n---\n")
    str_builder.append(f"Generated using [DocFxMarkdownGen](https://github.com/Jan0660/DocFxMarkdownGen) v{version_string}.\n")
    
    path = os.path.join(config.output_path, "index.md")
    with open(path, 'w', encoding='utf-8') as f:
        f.write("".join(str_builder))

@log_func(level=logging.INFO)
async def generate_markdown_files(config, items, type_counts):
    """Generate all markdown files"""
    with LogTimer("Generating all Markdown files"):
        type_tasks = []
        namespace_tasks = []
        missing_count = 0
        
        # Organize and count items by type for logging
        type_file_counts = {
            "Class": 0, "Interface": 0, "Enum": 0, "Struct": 0, 
            "Delegate": 0, "Namespace": 0
        }
        
        # Create tasks for each item
        for item in items:
            if item.comment_id is None:
                if item.type == "Namespace":
                    continue
                missing_count += 1
                logger.warning(f"Missing commentId for {item.uid or item.id or '(can\'t get uid or id)'}")
                continue
                
            if item.comment_id.startswith("T:"):
                type_file_counts[item.type] = type_file_counts.get(item.type, 0) + 1
                task = generate_type_markdown(config, item, items, type_counts)
                type_tasks.append(task)
            elif item.type == "Namespace":
                type_file_counts["Namespace"] += 1
                task = generate_namespace_markdown(config, item, items)
                namespace_tasks.append(task)
        
        # Log tasks information
        logger.info(f"Creating Markdown files: {sum(type_file_counts.values())} total files")
        
        # Log breakdown of file types
        file_types_info = ", ".join([f"{k}: {v}" for k, v in type_file_counts.items() if v > 0])
        logger.info(f"File type breakdown: {file_types_info}")
        
        if missing_count > 0:
            logger.warning(f"Skipping {missing_count} items with missing commentId")
        
        # Process namespaces first, then types, then index
        logger.info(f"Processing {len(namespace_tasks)} namespace files...")
        if namespace_tasks:
            await asyncio.gather(*namespace_tasks)
        
        logger.info(f"Processing {len(type_tasks)} type files...")
        if type_tasks:
            await asyncio.gather(*type_tasks)
        
        # Finally generate the index page
        logger.info("Generating index page...")
        await generate_index_markdown(config, items)
        
        logger.info("Markdown generation completed successfully")

@log_func(level=logging.INFO)
async def main():
    """Main function"""
    logger.info("DocFxMarkdownGen process starting")
    
    try:
        # Load configuration
        config = load_config()
        
        # Prepare output directory
        if os.path.exists(config.output_path):
            logger.info(f"Removing existing output directory: {config.output_path}")
            shutil.rmtree(config.output_path)
        
        logger.info(f"Creating output directory: {config.output_path}")
        os.makedirs(config.output_path, exist_ok=True)
        
        # Read YAML files - this is usually the longest step
        items = []
        with LogTimer("Reading and processing YAML files", level=logging.INFO):
            await read_yaml_files(config, items)
            logger.info(f"Processed {len(items)} total items")
        
        # Create namespace directories
        create_namespace_directories(config, items)
        
        # Count types for grouping
        type_counts = None
        if config.types_grouping and config.types_grouping.enabled:
            logger.info("Type grouping is enabled, counting types per namespace")
            type_counts = count_types(items)
        else:
            logger.info("Type grouping is disabled")
        
        # Generate and write markdown
        logger.info("Starting markdown generation process")
        await generate_markdown_files(config, items, type_counts)
        
        logger.info(f"DocFxMarkdownGen completed successfully")
        logger.info(f"Output written to: {os.path.abspath(config.output_path)}")
    
    except Exception as e:
        logger.error(f"DocFxMarkdownGen failed with error: {e}")
        logger.error("Stack trace:", exc_info=True)
        raise

if __name__ == "__main__":
    asyncio.run(main())
