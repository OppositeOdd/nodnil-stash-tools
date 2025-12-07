const fs = require('fs');
const css = fs.readFileSync('funscriptSceneTab.css', 'utf-8');

// Simple CSS validation checks
const issues = [];

// Check for balanced braces
const openBraces = (css.match(/{/g) || []).length;
const closeBraces = (css.match(/}/g) || []).length;
if (openBraces !== closeBraces) {
  issues.push(`Unbalanced braces: ${openBraces} open, ${closeBraces} close`);
}

// Check for missing semicolons (basic check)
const lines = css.split('\n');
lines.forEach((line, i) => {
  const trimmed = line.trim();
  if (trimmed &&
      !trimmed.startsWith('/*') &&
      !trimmed.endsWith('*/') &&
      !trimmed.endsWith('{') &&
      !trimmed.endsWith('}') &&
      !trimmed.endsWith(';') &&
      trimmed !== '' &&
      !trimmed.startsWith('//') &&
      trimmed !== '*') {
    // Check if it's a selector or property
    if (trimmed.includes(':') && !trimmed.includes('{')) {
      issues.push(`Line ${i + 1}: Missing semicolon? "${trimmed}"`);
    }
  }
});

// Check for duplicate properties in same rule
const ruleBlocks = css.match(/[^}]*{[^}]*}/g) || [];
ruleBlocks.forEach(block => {
  const props = {};
  const propLines = block.match(/[^{;]+:[^;]+;/g) || [];
  propLines.forEach(prop => {
    const key = prop.split(':')[0].trim();
    if (props[key]) {
      issues.push(`Duplicate property "${key}" in rule`);
    }
    props[key] = true;
  });
});

if (issues.length === 0) {
  console.log('✓ CSS validation PASSED');
  console.log(`  ${openBraces} rule blocks`);
  console.log(`  ${css.split('\n').filter(l => l.includes(':')).length} declarations`);
  process.exit(0);
} else {
  console.log('✗ CSS validation FAILED:');
  issues.forEach(issue => console.log(`  - ${issue}`));
  process.exit(1);
}
