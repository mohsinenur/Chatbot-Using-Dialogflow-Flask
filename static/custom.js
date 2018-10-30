function div_bottom() {
    var elem = document.getElementById('auto_scroll');
    elem.scrollTop = elem.scrollHeight;
    document.getElementById("input_message").focus();
}

function button_info(button_message){
     // return if the user does not enter any text
    if (!button_message) {
      return
    }

    $('.chat-container').append(`
        // remove the loading indicator
        $( "#loading" ).remove();
        <div class="text_human">
             
                <span> ${button_message}</span>
              
        </div>
    `)

    // loading
    $('.chat-container').append(`
        <div class="text_bot" id="loading">
                <span><b>...</b></span>
        </div>
    `)
    // clear the text input
    $('#input_message').val('')

    // send the message
    submit_message(button_message)
    div_bottom()
}

function submit_message(message) {
    $.post( "/send_message", {message: message}, handle_response);

    function handle_response(data) {
        if (data.message == 'Banking Query' || data.message.indexOf("What kind of query you have?") >= 0) {
            $('.chat-container').append(`
                    <div class="text_bot">
                            <span>${data.message}</span></br>
                        <div id="balance_button" class="btn btn-outline-success btn-sm m-1">Balance Check</div>
                        <div id="history_button" class="btn btn-outline-success btn-sm m-1">History</div>
                        <div id="stop_cheque_button" class="btn btn-outline-success btn-sm m-1">Stop Cheque / Stop Card</div>
                        <div id="chequebook_button" class="btn btn-outline-success btn-sm m-1">Cheque Book Request</div>
                    </div>
              `)
              // remove the loading indicator
                $( "#loading" ).remove();
                div_bottom()
        }
        else if (data.message == 'Please, Select an operator below...') {
            $('.chat-container').append(`
                    <div class="text_bot">
                        <span>${data.message}</span></br>
                        <div id="gp_button" class="btn btn-outline-success btn-sm m-1">Grameenphone</div>
                        <div id="airtel_button" class="btn btn-outline-success btn-sm m-1">Airtel</div>
                        <div id="robi_button" class="btn btn-outline-success btn-sm m-1">Robi</div>
                        <div id="banglalink_button" class="btn btn-outline-success btn-sm m-1">Banglalink</div>
                        <div id="telitalk_button" class="btn btn-outline-success btn-sm m-1">Telitalk</div>
                    </div>
              `)
              // remove the loading indicator
                $( "#loading" ).remove();
                div_bottom()
        }
        else if (data.message.indexOf("How can I help you?") >= 0 || data.message == 'Services' || data.message == 'Could not understand.' || data.message == 'Account not found.') {
            $('.chat-container').append(`
                    <div class="text_bot" style="">
                        <span>${data.message}</span>
                        <span> Select quick link below </span></br>
                        <div id="banking_query_btn" class="btn btn-outline-success btn-sm m-1">Banking Query</div>
                        <div id="topup_button" class="btn btn-outline-success btn-sm m-1">Top Up</div>
                        <div id="general_info_btn" class="btn btn-outline-success btn-sm m-1">General Information</div>
                    </div>
              `)
              // remove the loading indicator
                $( "#loading" ).remove();
                div_bottom()
        }
        else if (data.message == 'Topup successful.' || data.message.indexOf("cheque book request accepted") >= 0 || data.message.indexOf("Your tranjection history below") >= 0 || data.message.indexOf("Thanks for your information.") >= 0 || data.message.indexOf("taka in account no") >= 0 || data.message.indexOf("Terms And Conditions") >= 0 || data.message.indexOf("About Bank") >= 0) {
            $('.chat-container').append(`
                    <div class="text_bot" style="">
                        <span>${data.message}</span>
                        <span>Have more query? Select quick link below </span></br>
                        <div id="banking_query_btn" class="btn btn-outline-success btn-sm m-1">Banking Query</div>
                        <div id="topup_button" class="btn btn-outline-success btn-sm m-1">Top Up</div>
                        <div id="general_info_btn" class="btn btn-outline-success btn-sm m-1">General Information</div>
                    </div>
              `)
              // remove the loading indicator
                $( "#loading" ).remove();
                div_bottom()
        }
        else if (data.message == "It's prepaid or postpaid?") {
            $('.chat-container').append(`
                    <div class="text_bot" style="">
                        <span>${data.message}</span></br>
                        <div id="prepaid_btn" class="btn btn-outline-success btn-sm m-1">Prepaid</div>
                        <div id="postpaid_btn" class="btn btn-outline-success btn-sm m-1">Postpaid</div>
                    </div>
              `)
              // remove the loading indicator
                $( "#loading" ).remove();
                div_bottom()
        }
        else if (data.message == "What kind of information?") {
            $('.chat-container').append(`
                    <div class="text_bot" style="">
                        <span>${data.message}</span></br>
                        <div id="about_btn" class="btn btn-outline-success btn-sm m-1">About Bank</div>
                        <div id="terms_btn" class="btn btn-outline-success btn-sm m-1">Terms And Conditions</div>
                    </div>
              `)
              // remove the loading indicator
                $( "#loading" ).remove();
                div_bottom()
        }
        else if (data.message == "How many pages?") {
            $('.chat-container').append(`
                    <div class="text_bot" style="">
                        <span>${data.message}</span></br>
                        <div id="num10_btn" class="btn btn-outline-success btn-sm m-1">10</div>
                        <div id="num25_btn" class="btn btn-outline-success btn-sm m-1">25</div>
                        <div id="num50_btn" class="btn btn-outline-success btn-sm m-1">50</div>
                    </div>
              `)
              // remove the loading indicator
                $( "#loading" ).remove();
                div_bottom()
        }
        else {
            // append the bot repsonse to the div
              $('.chat-container').append(`
                    <div class="text_bot">
                            <span>${data.message}</span>
                    </div>
              `)
              // remove the loading indicator
              $( "#loading" ).remove();
              div_bottom()
        }
    }
}

$('#target').on('submit', function(e){
    e.preventDefault();
    const input_message = $('#input_message').val()
    // return if the user does not enter any text
    if (!input_message) {
      return
    }

    $('.chat-container').append(`
        <div class="text_human">
                <span> ${input_message}</span>
        </div>
    `)

    // loading
    $('.chat-container').append(`
        <div class="text_bot" id="loading">
                <span><b>...</b></span>
        </div>
    `)

    // clear the text input
    $('#input_message').val('')

    // send the message
    submit_message(input_message)
    div_bottom()
});


$('.chat-container').on('click', '#banking_query_btn', function (e) {
    e.preventDefault();
    const button_message = 'Banking Query'
    button_info(button_message)
});

$('.chat-container').on('click', '#general_info_btn', function (e) {
    e.preventDefault();
    const button_message = 'General Information'
    button_info(button_message)
});

$('.chat-container').on('click', '#help_btn', function (e) {
    e.preventDefault();
    const button_message = 'Help'
    button_info(button_message)
});

$('.chat-container').on('click', '#services_btn', function (e) {
    e.preventDefault();
    const button_message = 'Services'
    button_info(button_message)
});

$('.chat-container').on('click', '#email_button', function (e) {
    e.preventDefault();
    const button_message = 'Email'
    button_info(button_message)
});

$('.chat-container').on('click', '#phone_button', function (e) {
    e.preventDefault();
    const button_message = 'Phone'
    button_info(button_message)
});

$('.chat-container').on('click', '#balance_button', function (e) {
    e.preventDefault();
    const button_message = 'Balance Check'
    button_info(button_message)
});

$('.chat-container').on('click', '#history_button', function (e) {
    e.preventDefault();
    const button_message = 'History'
    button_info(button_message)
});

$('.chat-container').on('click', '#topup_button', function (e) {
    e.preventDefault();
    const button_message = 'Top Up'
    button_info(button_message)
});

$('.chat-container').on('click', '#stop_cheque_button', function (e) {
    e.preventDefault();
    const button_message = 'Stop Cheque'
    button_info(button_message)
});

$('.chat-container').on('click', '#chequebook_button', function (e) {
    e.preventDefault();
    const button_message = 'Cheque Book Request'
    button_info(button_message)

});

$('.chat-container').on('click', '#gp_button', function (e) {
    e.preventDefault();
    const button_message = 'Grameenphone'
    button_info(button_message)
});

$('.chat-container').on('click', '#banglalink_button', function (e) {
    e.preventDefault();
    const button_message = 'Banglalink'
    button_info(button_message)
});
$('.chat-container').on('click', '#airtel_button', function (e) {
    e.preventDefault();
    const button_message = 'Airtel'
    button_info(button_message)
});
$('.chat-container').on('click', '#robi_button', function (e) {
    e.preventDefault();
    const button_message = 'Robi'
    button_info(button_message)
});
$('.chat-container').on('click', '#telitalk_button', function (e) {
    e.preventDefault();
    const button_message = 'Telitalk'
    button_info(button_message)
});
$('.chat-container').on('click', '#prepaid_btn', function (e) {
    e.preventDefault();
    const button_message = 'Prepaid'
    button_info(button_message)
});
$('.chat-container').on('click', '#postpaid_btn', function (e) {
    e.preventDefault();
    const button_message = 'Postpaid'
    button_info(button_message)
});
$('.chat-container').on('click', '#about_btn', function (e) {
    e.preventDefault();
    const button_message = 'About Bank'
    button_info(button_message)
});
$('.chat-container').on('click', '#terms_btn', function (e) {
    e.preventDefault();
    const button_message = 'Terms And Conditions'
    button_info(button_message)
});
$('.chat-container').on('click', '#num10_btn', function (e) {
    e.preventDefault();
    const button_message = '10'
    button_info(button_message)
});
$('.chat-container').on('click', '#num25_btn', function (e) {
    e.preventDefault();
    const button_message = '25'
    button_info(button_message)
});
$('.chat-container').on('click', '#num50_btn', function (e) {
    e.preventDefault();
    const button_message = '50'
    button_info(button_message)
});
