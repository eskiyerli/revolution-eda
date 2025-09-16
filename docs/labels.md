# Labels

## createNLPLabel method

This `createNLPLabel` method parses **Natural Language Parameter (NLP) labels** used in Revolution EDA's symbol system.

## Purpose

Converts label definitions like `[@width:W=%:W=10u]` into usable label components for display and parameter management.

## Input Format

- `[@name:format:default]` - Standard NLP label syntax
- `[@name]` - Simple name-only labels
- Predefined labels like `[@instName]`, `[@cellName]`

## Processing Logic

1. **Validation**: Checks for proper `[@...]` bracket format
2. **Parsing**: Splits on `:` to extract name, format, and default value
3. **Context Handling**:
   - Symbol editor: Returns raw definition
   - Predefined labels: Uses special handling for system labels
   - Regular labels: Processes format and default values

## Output Components

Returns a tuple `(labelName, labelText, labelValue)`:

- **labelName**: Parameter identifier (e.g., "width")
- **labelText**: Display text with formatting applied (e.g., "W=10u")
- **labelValue**: Current parameter value (e.g., "10u")

## Key Features

- **Format substitution**: Replaces `%` with actual values
- **Default values**: Handles `key=value` syntax in defaults
- **Error handling**: Returns empty strings on parse failures
- **Flexible syntax**: Supports various label complexity levels

