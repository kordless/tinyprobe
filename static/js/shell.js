TerminalShell.filters.push(function (terminal, cmd) {
	if (/!!/.test(cmd)) {
		var newCommand = cmd.replace('!!', this.lastCommand);
		terminal.print(newCommand);
		return newCommand;
	} else {
		return cmd;
	}
});

// builtin shell command for exiting
TerminalShell.commands['logout'] =
TerminalShell.commands['exit'] = 
TerminalShell.commands['quit'] = function(terminal) {
	terminal.print('Logout complete.  Clearing session info.');
	$('#prompt, #cursor').hide();
	terminal.promptActive = false;
	window.location = '/logout';
	return false;
};

// builtin shell command for closing window
TerminalShell.commands['close'] = function(terminal) {
	terminal.print('Smell you later.');
	$('#prompt, #cursor').hide();
	terminal.promptActive = false;
	window.close();
	return false;
};

function linkFile(url) {
	return {type:'dir', enter:function() {
		window.location = url;
	}};
}


TerminalShell.commands['wget'] = TerminalShell.commands['curl'] = function(terminal, dest) {
	if (dest) {
		terminal.setWorking(true);
		var browser = $('<div>')
			.addClass('browser')
			.append($('<iframe>')
					.attr('src', dest).width("100%").height(600)
					.one('load', function() {
						terminal.setWorking(false);
					}));
		terminal.print(browser);
		return browser;
	} else {
		terminal.print("Please specify a URL.");
	}
};

TerminalShell.commands['help'] = function (terminal, command) {
	if (!command) {
		terminal.print('Available commands are:');
		cmd_list = $('<ul>');
		$.each(this.commands, function(name, func) {
			cmd_list.append($('<li>').text(name));
		});
		terminal.print(cmd_list);
		terminal.print("Type 'help <command>' for more help.");
    } else {
	    // api call for help for command
	    terminal.print("would show help for "+command+".");
	}
},

TerminalShell.commands['irc'] = function(terminal, nick) {
	if (nick) {
		$('.irc').slideUp('fast', function() {
			$(this).remove();
		});
		var url = "http://widget.mibbit.com/?server=irc.foonetic.net&channel=%23tinyprobe";
		if (nick) {
			url += "&nick=" + encodeURIComponent(nick);
		}
		TerminalShell.commands['curl'](terminal, url).addClass('irc');
	} else {
		terminal.print('usage: irc <nick>');
	}
};

TerminalShell.commands['status'] = function(terminal, stuff) {
	terminal.print("All systems go.  Type a command or 'help'.");
	terminal.print("");
};

TerminalShell.commands['theme'] = function(terminal, stuff) {
	if (!stuff) {
		terminal.print("Specify a color theme.  Choices are 'cobalt', 'black' and 'white'.")
	} else if (stuff.toLowerCase() == 'white') {
		terminal.print("Changing theme to white.");
		$("body").css("background-color", "#eeeeee");
		$("pre, td, th, p, div").css("color", "#444444");
	}
};

// external javascript commands from server
TerminalShell.commands['foobar'] = function (terminal, stuff) {
	$.getScript("static/js/foobar.js").done(function(script, textStatus) {});
}

// one line text output
function oneLiner(terminal, msg, msgmap) {
	if (msgmap.hasOwnProperty(msg)) {
		terminal.print(msgmap[msg]);
		return true;
	} else {
		return false;
	}
}

TerminalShell.fallback = function(terminal, cmd_name, cmd_args, cmd_text) {
	oneliners = {
		'make': 'Making a sandwitch.',
		'emacs': 'We prefer vi around here.',
		'vim': 'We prefer emacs around here.',
		'vi': 'We prefer nano around here.',
		'nano': 'We prefer vim around here.',
		'ls': "I know it looks like a terminal, but it's not.",
	};

	cmd_name = cmd_name.toLowerCase();
	$cmd_args = cmd_args;
	$cmd_text = cmd_text;

	if (!oneLiner(terminal, cmd_name, oneliners)) {
		$cmd_args = cmd_args;
		$cmd_name = cmd_name;
        $.getScript("/js/commands/"+cmd_name+".js") 
		.done(function(script, textStatus) {
		})
		.fail(function(jqxhr, settings, exception) {
		  terminal.print("Remote execution failure: "+exception);
		});
	}
	return true;
};

$(document).ready(function() {
	$terminal = Terminal;
	Terminal.promptActive = false;
	$('#screen').bind('cli-load', function(e) {
		Terminal.promptActive = true;
		Terminal.runCommand('status');
	});
});