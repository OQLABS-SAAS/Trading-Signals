var fs=require("fs");
var h=fs.readFileSync("static/index-v2-prototype.html","utf8");
var blocks=h.match(/<script[^>]*>([\s\S]*?)<\/script>/g)||[];
var all="";
blocks.forEach(function(b){
  all+=b.replace(/<script[^>]*>/,"").replace(/<\/script>/,"")+"\n";
});
fs.writeFileSync("/tmp/_full_js.js", all);
