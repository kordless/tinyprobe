$(document).ready(function() {
	$.getScript("/js/libs/base64.js") 
	.done(function(script, textStatus) {
		data = {'text':$cmd_text};
		data_encoded = JSON.stringify(data);
		data_base64 = Base64.encode(data_encoded);
		$.getJSON('/input/adsfadsfasdfasdfasdf?data='+data_base64, function() {} );
	})
	.fail(function(jqxhr, settings, exception) {
	    $terminal.print("Remote execution failure: "+exception);
	});
});