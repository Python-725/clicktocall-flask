// Execute JavaScript on page load
$(function() {
    // Initialize phone number text input plugin
    $('#sourceNumber').intlTelInput({
        responsiveDropdown: true,
        autoFormat: true,
        utilsScript: '/static/js/libphonenumber/src/utils.js'
    });
    $('#destinationNumber').intlTelInput({
        responsiveDropdown: true,
        autoFormat: true,
        utilsScript: '/static/js/libphonenumber/src/utils.js'
    });

    // Intercept form submission and submit the form with ajax
    $('#contactForm').on('submit', function(e) {
        // Prevent submit event from bubbling and automatically
        // submitting the form
        e.preventDefault();

        // Call our ajax endpoint on the server to initialize the
        // phone call
        $.ajax({
            url: '/call',
            method: 'POST',
            dataType: 'json',
            data: {
                source_number: $('#sourceNumber').val(),
                dest_number: $('#destinationNumber').val()
            }
        }).done(function(data) {
            // The JSON sent back from the server will contain
            // a success message
            alert(data.message);
        }).fail(function(data) {
            alert(data.responseJSON.error);
        });
    });
});
