$(document).ready(function() {
	chart_id = "chart-" + (new Date).getTime();
	if ($cmd_args.indexOf("status") != -1) {
	    $terminal.print($('<div style="height: 300px; width: 500px; margin-top: 20px;" id="'+chart_id+'"></div>'));
		(function basic_pie(container) {
		  var
		    d1 = [[0, 4]],
		    d2 = [[0, 3]],
		    d3 = [[0, 1.03]],
		    d4 = [[0, 3.5]],
		    d5 = [[0, 3.5]],
		    graph;
 
		  graph = Flotr.draw(container, [
			{ data : d1, label : '501' },
		    { data : d2, label : '404' },
		    { data : d3, label : '401' },
		    { data : d4, label : '302',
		      pie : {
		        explode : 50
		      }
		    },
		    { data : d5, label : '200' }
		  ], {
		    HtmlText : false,
		    grid : {
		      verticalLines : false,
		      horizontalLines : false
		    },
		    xaxis : { showLabels : false },
		    yaxis : { showLabels : false },
		    pie : {
		      show : true, 
		      explode : 6
		    },
		    mouse : { track : true },
		    legend : {
		      position : 'se',
		      backgroundColor : '#ffffff'
		    }
		  });
		})(document.getElementById(chart_id));
	} else if ($cmd_args.indexOf("events") != -1) {
	    $terminal.print($('<div style="height: 300px; width: 1024px; margin-top: 20px;" id="'+chart_id+'"></div>'));
		(function basic_bars(container, horizontal) {
		  var
		    horizontal = (horizontal ? true : false), // Show horizontal bars
		    d1 = [],                                  // First data series
		    d2 = [],                                  // Second data series
		    point,                                    // Data point variable declaration
		    i;

		  for (i = 0; i < 100; i++) {

		    if (horizontal) { 
		      point = [Math.ceil(Math.random()*100), i];
		    } else {
		      point = [i, Math.ceil(Math.random()*100)];
		    }

		    d1.push(point);

		    if (horizontal) { 
		      point = [Math.ceil(Math.random()*10), i+0.5];
		    } else {
		      point = [i+0.5, Math.ceil(Math.random()*10)];
		    }

		    d2.push(point);
		  };

		  // Draw the graph
		  Flotr.draw(
		    container,
		    [d1, d2],
		    {
		      bars : {
		        show : true,
		        horizontal : horizontal,
		        shadowSize : 0,
		        barWidth : 0.5
		      },
		      grid : {
		        verticalLines : false,
		        horizontalLines : false
		      },
		      mouse : {
		        track : true,
		        relative : true
		      },
		      yaxis : {
		        min : 0,
		        autoscaleMargin : 1
		      }
		    }
		  );
		})(document.getElementById(chart_id));
	}
}); // close document ready
