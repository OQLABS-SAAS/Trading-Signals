const fs = require('fs');
const html = fs.readFileSync('static/index-v2-prototype.html', 'utf8');
const blocks = html.match(/<script[^>]*>([\s\S]*?)<\/script>/g) || [];
let braces = 0, parens = 0, bt = false;
blocks.forEach(b => {
  const js = b.replace(/<script[^>]*>/, '').replace(/<\/script>/, '');
  for(let c of js) {
    if(c === '{') braces++; if(c === '}') braces--;
    if(c === '(') parens++; if(c === ')') parens--;
    if(c === '`') bt = !bt;
  }
});
console.log('Braces:', braces, 'Parens:', parens, 'Backtick:', bt);
if(braces !== 0 || parens !== 0 || bt) process.exit(1);
console.log('JS syntax OK');
