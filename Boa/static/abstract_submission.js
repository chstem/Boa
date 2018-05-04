
var active_input;

$.ajaxSetup({
    beforeSend: function(xhr, settings) {
        if (!/^(GET|HEAD|OPTIONS|TRACE)$/i.test(settings.type) && !this.crossDomain) {
            xhr.setRequestHeader("X-CSRFToken", csrftoken)
        }
    }
})

$(document).ready(function () {

    // hide buttons to remove authors/affiliations
    if ($('div[id^=author_]').length == 1) {
        $('#rmauth_0').hide(speed=0);
    };
    if ($('div[id^=affiliation_]').length == 1) {
        $('#rmaffil_0').hide(speed=0);
    };

    // enable title/institute alt fields
    $('[id^=affiliations-][id$=institute_alt]').each(function() {
        var id = this.id.split('-')[1];
        $(this).prop('disabled', $('#affiliations-'+id+'-institute').find(':selected').val() != 'other');
    });

    // fill fields with presets
    $(document).on('change', '.select_inst', function () {

        var id = this.id.split('-')[1];
        var selected_institute = $(this).find(':selected').text();

        switch (selected_institute) {

            case '(please choose)':
                $('#affiliations-'+id+'-institute_alt').prop('disabled', true);
                $('#affiliations-'+id+'-institute_alt').val('');
                break;
            case 'other (please enter):':
                $('#affiliations-'+id+'-institute_alt').prop('disabled', false);
                $('#affiliations-'+id+'-institute_alt').val('');
                $('#affiliations-'+id+'-department').val('');
                $('#affiliations-'+id+'-street').val('');
                $('#affiliations-'+id+'-postal_code').val('');
                $('#affiliations-'+id+'-city').val('');
                //$('#affiliations-'+id+'-country').val( '{{ default_country_id }}' );
                break;
            default:
                for (var ii = 0; ii < institute_presets.length; ii++) {
                    if (institute_presets[ii][0] == selected_institute) {
                        $('#affiliations-'+id+'-institute_alt').prop('disabled', true);
                        $('#affiliations-'+id+'-institute_alt').val('');
                        $('#affiliations-'+id+'-department').val(institute_presets[ii][1]);
                        $('#affiliations-'+id+'-street').val(institute_presets[ii][2]);
                        $('#affiliations-'+id+'-postal_code').val(institute_presets[ii][3]);
                        $('#affiliations-'+id+'-city').val(institute_presets[ii][4]);
                        $('#affiliations-'+id+'-country').val(institute_presets[ii][5]);
                        break;
                    };
                };

        };

    });

    // add/remove authors/affiliations
    $(document).on('click', '.rmauth', function () {

        if ($('div[id^=author_]').length > 1) {

            var this_id = this.id.split('_')[1];

            // remove author div
            $('#author_' + this_id).remove();

            // hide Main Author button
            if ($('div[id^=author_]').length == 1) {
                $('#rmauth_0').hide(speed=0);
            };

            // updates indices of following authors divs
            $('div[id^=author_]').each( function() {

                var id = this.id.split('_')[1];

                if ( parseInt(id) >= parseInt(this_id) ) {

                    var id_new = parseInt(id) - 1;
                    var regex = new RegExp(id, 'g');

                    // update Author label
                    if (id_new == 0) {
                        $(this).find('.title').text('Main Author');
                    } else {
                        $(this).find('.title').text('Author ' + (id_new+1));
                    };

                    // update input/select ids and names
                    $(this).find('[id^=authors-]').each ( function(index, element) {
                        element.id = element.id.replace(regex, id_new);
                        element.name = element.name.replace(regex, id_new);
                    });

                    // update labels
                    $(this).find('label[for^=authors-]').each ( function(index, element) {
                        element.htmlFor = element.htmlFor.replace(regex, id_new);
                    });

                    // update buttons
                    $(this).find('button[id^=rmauth_]').each( function(index, element) {
                        element.id = element.id.replace('rmauth_'+id, 'rmaffil_'+id_new);
                    });

                    // update div id
                    this.id = this.id.replace(regex, id_new);
                };

            });

        };

    });

    $(document).on('click', '.rmaffil', function () {

        if ($('div[id^=affiliation_]').length > 1) {

            var this_id = this.id.split('_')[1];

            // remove affiliation div
            $('#affiliation_' + this_id).remove();

            // hide Affiliation 1 button
            if ($('div[id^=affiliation_]').length == 1) {
                $('#rmaffil_0').hide(speed=0);
            };

            // updates indices of following affiliation divs
            $('div[id^=affiliation_]').each( function() {

                var id = this.id.split('_')[1];

                if ( parseInt(id) >= parseInt(this_id) ) {

                    var id_new = parseInt(id) - 1;

                    // update Affiliation label
                    $(this).find('.title').text('Affiliation ' + (id_new+1));

                    // update input/select ids and names
                    var regex = new RegExp('affiliations-'+id+'-', 'g');
                    $(this).find('[id^=affiliations-]').each ( function(index, element) {
                        element.id = element.id.replace(regex, 'affiliations-'+id_new+'-');
                        element.name = element.name.replace(regex, 'affiliations-'+id_new+'-');
                    });

                    // update labels
                    $(this).find('[for^=affiliations-]').each ( function(index, element) {
                        element.htmlFor = element.htmlFor.replace(regex, 'affiliations-'+id_new+'-');
                    });

                    // update buttons
                    $(this).find('[id^=rmaffil_]').each( function(index, element) {
                        element.id = element.id.replace('rmaffil_'+id, 'rmaffil_'+id_new);
                    });

                    // update div id
                    this.id = this.id.replace('affiliation_'+id, 'affiliation_'+id_new);

                };

            });

            // update author affiliation keys
            $('div[id^=author_]').each( function() {

                var id = this.id.split('_')[1];
                var ids = $('#authors-'+id+'-affiliations').val();
                var ids_new = '';

                for (var i = 0, len = ids.length; i < len; i++) {
                    var key = parseInt(ids.charAt(i));
                    if ( key-1 > parseInt(this_id) ){
                        ids_new = ids_new + (key-1).toString();
                    } else {
                        ids_new = ids_new + ids.charAt(i);
                    };
                };

                $('#authors-'+id+'-affiliations').val(ids_new);

            });

        };

    });

    $('#addauth').click( function () {

        if ($('div[id^=author_]').length < 9) {

            // show Main Author button
            $('#rmauth_0').show(speed=0);

            // create html from template
            var newauthor = $('#author_0').clone();
            var template = newauthor.html();
            var id = $('div[id^=author_]').length;

            template = template.replace(/-0-/g, '-'+id+'-');
            template = template.replace(/Main Author/g, 'Author '+(id+1).toString());
            template = template.replace(/rmauth_0/g, 'rmauth_'+id);
            newauthor.html(template);
            newauthor.attr('id', 'author_'+id.toString());

            $('#author_'+(id-1).toString()).after(newauthor);

            // set label and clear fields
            $('#authors-'+id+'-firstname').val('');
            $('#authors-'+id+'-lastname').val('');
            $('#authors-'+id+'-affiliations').val('');

        };

    });

    $('#addaffil').click( function () {

        if ($('div[id^=affiliation_]').length < 9) {

            // show Affiliation 1 button
            $('#rmaffil_0').show(speed=0);

            // create html from template
            var newaffil = $('#affiliation_0').clone();
            var template = newaffil.html();
            var id = $('div[id^=affiliation_]').length;

            template = template.replace(/Affiliation 1/g, 'Affiliation '+(id+1).toString());
            template = template.replace(/<option selected="" value=/, '<option value=');
            template = template.replace('affiliation_0', 'affiliation_'+id);
            template = template.replace('rmaffil_0', 'rmaffil_'+id);
            template = template.replace(/affiliations-0-/g, 'affiliations-'+id+'-');
            newaffil.html(template);
            newaffil.attr('id', 'affiliation_'+id.toString());

            $('#affiliation_'+(id-1).toString()).after(newaffil);

            // set label and clear fields
            if (institute_presets.length > 0) {
                $('#affiliations-'+id+'-institute').val('pls_choose');
                $('#affiliations-'+id+'-institute_alt').val('');
                $('#affiliations-'+id+'-institute_alt').prop('disabled', true);
            } else {
                $('#affiliations-'+id+'-institute').val('');
            };
            $('#affiliations-'+id+'-department').val('');
            $('#affiliations-'+id+'-street').val('');
            $('#affiliations-'+id+'-postal_code').val('');
            $('#affiliations-'+id+'-city').val('');
            $('#affiliations-'+id+'-country').val(default_country_id);

        };

    });

    // save last clicked input to use for LaTeX Buttons
    $(document).on('click', '.enable_buttons', function () {
        active_input = this;
    });

    // reset for all other inputs
    $(document).on('click', ':input:not(.enable_buttons):not(.btn)', function () {
        active_input = undefined;
    });

});

// LaTeX Buttons
function insert(aTag, eTag) {

    // get active field
    if (typeof active_input == 'undefined') {
        alert('Please choose a valid entry field first.');
        return;
        var input = document.getElementById('content');
        input.focus();
    } else {
        var input = active_input;
    };

    /* for Internet Explorer */
    if(typeof document.selection != 'undefined') {
        /* insert text */
        var range = document.selection.createRange();
        var insText = range.text;
        range.text = aTag + insText + eTag;
        /* set cursor position */
        range = document.selection.createRange();
        if (insText.length == 0) {
            range.move('character', -eTag.length);
        } else {
            range.moveStart('character', aTag.length + insText.length + eTag.length);
        }
        range.select();
    }

    /* for Gecko based browsers */
    else if(typeof input.selectionStart != 'undefined'){

        /* insert text */
        var start = input.selectionStart;
        var end = input.selectionEnd;
        var insText = input.value.substring(start, end);
        input.value = input.value.substr(0, start) + aTag + insText + eTag + input.value.substr(end);
        /* set cursor position */
        var pos;
        if (insText.length == 0) {
            pos = start + aTag.length;
        } else {
            pos = start + aTag.length + insText.length + eTag.length;
        }
        input.selectionStart = pos;
        input.selectionEnd = pos;
    }

//     /* for other browsers */
//     else
//     {
//         /* get position to insert text */
//         var pos;
//         var re = new RegExp('^[0-9]{0,3}$');
//         while(!re.test(pos)) {
//             pos = prompt("Einfuegen an Position (0.." + input.value.length + "):", "0");
//         }
//         if(pos > input.value.length) {
//             pos = input.value.length;
//         }
//         /* insert text */
//         var insText = prompt("Bitte geben Sie den zu formatierenden Text ein:");
//         input.value = input.value.substr(0, pos) + aTag + insText + eTag + input.value.substr(pos);
//     }

}
