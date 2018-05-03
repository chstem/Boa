
$(document).ready(function () {

    $('#title_alt').prop('disabled', $('.select_title').val() != 'other');
    $('#institute_alt').prop('disabled', $('.select_inst').find(':selected').val() != 'other');

    $('.select_title').change(function () {

        var select_title = document.getElementById('title');
        var txt_title = document.getElementById('title_alt');

        if ($(this).val() == 'other') {
            $('#title_alt').prop('disabled', false);
        } else {
            $('#title_alt').prop('disabled', true);
        }
        $('#title_alt').val('');

    });

    $('.select_inst').change(function () {

        var selected_institute = $(this).find(':selected').text();

        switch (selected_institute) {

            case '(please choose)':
                $('#institute_alt').prop('disabled', true);
                $('#institute_alt').val('');
                break;
            case 'other (please enter):':
                $('#institute_alt').prop('disabled', false);
                $('#institute_alt').val('');
                $('#address_line1').val('');
                $('#address_line2').val('');
                $('#department').val('');
                $('#street').val('');
                $('#postal_code').val('');
                $('#city').val('');
                //$('#country').val( '{{ default_country_id }}' );
                break;
            default:
                for (var ii = 0; ii < institute_presets.length; ii++) {
                    if (institute_presets[ii][0] == selected_institute) {
                        $('#institute_alt').prop('disabled', true);
                        $('#institute_alt').val('');
                        $('#department').val(institute_presets[ii][1]);
                        $('#address_line1').val(institute_presets[ii][0]);
                        $('#address_line2').val(institute_presets[ii][1]);
                        $('#street').val(institute_presets[ii][2]);
                        $('#postal_code').val(institute_presets[ii][3]);
                        $('#city').val(institute_presets[ii][4]);
                        $('#country').val(institute_presets[ii][5]);
                        break;
                    };
                };

        };

    });

    $('#department').keyup(function () {
        $('#address_line2').val($('#department').val());
    });

    $('#institute_alt').keyup(function () {
        $('#address_line1').val($('#institute_alt').val());
    });

});
