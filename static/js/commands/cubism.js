$(document).ready(function() {

// add styles
var css = '.horizon .title, .horizon .value {text-shadow: 0 1px 0 rgba(255, 255, 255, .5);white-space: nowrap; background-color: #444;}'
, head = document.getElementsByTagName('head')[0], style = document.createElement('style');

style.type = 'text/css';
if(style.styleSheet){
    style.styleSheet.cssText = css;
}else{
    style.appendChild(document.createTextNode(css));
}
head.appendChild(style);

// random number generator
function random(name) {
  var value = 0,
      values = [],
      i = 0,
      last;
  return context.metric(function(start, stop, step, callback) {
    start = +start, stop = +stop;
    if (isNaN(last)) last = start;
    while (last < stop) {
      last += step;
      value = Math.max(-10, Math.min(10, value + .8 * Math.random() - .4 + .2 * Math.cos(i += .2)));
      values.push(value);
    }
    callback(null, values = values.slice((start - stop) / step));
  }, name);
}

var context = cubism.context()
.serverDelay(0)
.clientDelay(0)
.step(1e3);

var foo = random("foo");
var bar = random("bar");

chart_id = "chart-" + (new Date).getTime();
$terminal.print($('<div style="min-height: 50px; width: 800; border: none;" id="'+chart_id+'"></div>'));

d3.select("#"+chart_id).call(function(div) {
  div.datum(foo);

  div.append("div")
      .attr("class", "horizon")
      .call(context.horizon()
        .height(50)
        .mode("mirror")
        .colors(["#bdd7e7","#bae4b3"])
        .title("")
        .extent([-10, 10]));
});

context.on("focus", function(i) {
  d3.selectAll(".value").style("right", i == null ? null : context.size() - i + "px");
});

});