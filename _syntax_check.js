const fs = require('fs');
const vm = require('vm');
const html = fs.readFileSync('static/index-v2-prototype.html', 'utf8');
const blocks = html.match(/<script[^>]*>([\s\S]*?)<\/script>/g) || [];
let all = '';
blocks.forEach((b) => {
  all += b.replace(/<script[^>]*>/, '').replace(/<\/script>/, '') + '\n';
});

try {
  new vm.Script(all, { filename: 'static/index-v2-prototype.html <script>' });
} catch (error) {
  console.error(error && error.stack ? error.stack : error);
  process.exit(1);
}

console.log('JS syntax OK');
