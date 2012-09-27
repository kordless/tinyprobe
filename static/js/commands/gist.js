$(document).ready(function() {
	item_id = "item-" + (new Date).getTime();
	$terminal.print($('<div id="'+item_id+'">foo</div>'));
});