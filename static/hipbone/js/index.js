function activate_overlay(bool, element_id) {
    document.getElementById(element_id).style.opacity = (bool ? 0.5 : 1.0);
}

$(document).ready(function () {

});

function populate_table(data, table_id, td_class) {
    var thead = table_id + " thead";
    var cols = $(thead).length;
    $(table_id + " > tbody").empty(); // Try replacing this with $(table_id).find("tbody tr").remove();
    var tbody = table_id + " tbody";
    if (td_class) {
        var td_class_str = " class='" + td_class + "'";
    } else {
        var td_class_str = "";
    }

    if (data.length == 0) {
        $(tbody).append('<tr><td colspan="' + cols + '">No results.</td></tr>');
    } else {
        // Create tr elements for tbody from data (a JavaScript object with
        // an arbitrary number of key-value pairs)
        data.forEach(function (datum) {
            var row = "<tr>";
            for (var key of Object.keys(datum)) {
                row += "<td" + td_class_str + ">" + datum[key] + "</td>";
            }

            row += "</tr>";
            $(tbody).append(row);
        });
    }

}

function populate_grouped_table(data, table_id, td_class) {
    var thead = table_id + " thead";
    var cols = $(thead).length;
    $(table_id + " > tbody").empty(); // Try replacing this with $(table_id).find("tbody tr").remove();
    var tbody = table_id + " tbody";
    if (td_class) {
        var td_class_str = " class='" + td_class + "'";
        var td_class_str_first = " class='" + td_class + " divider' style='border-top: 3px solid black;'";
    } else {
        var td_class_str = "";
        var td_class_str_first = " class='divider' style='border-top: 3px solid black;'";
    }

    if (data.length == 0) {
        $(tbody).append('<tr><td colspan="' + cols + '">No results.</td></tr>');
    } else {
        // Create tr elements for tbody from data (a JavaScript array with
        // an arbitrary number of arrays of key-value pairs)
        let record_count = 0;
        for (let record of data) {
            let row_count = 0;
            for (let pair of record) {
                //if (row_count == 0) {
                //    var row = "<tr class='bold'>";
                //} else {
                var row = "<tr>";
                //}
                for (var key of Object.keys(pair)) {
                    row += "<td";
                    if ((record_count === 0) || (row_count > 0)) {
                        row += td_class_str;
                    } else {
                        row += td_class_str_first;
                    }

                    row += ">" + pair[key] + "</td>";
                }

                row += "</tr>";
                $(tbody).append(row);
                row_count++;
            }

            record_count++;
        }

    }

}

function refresh_parcel() {
    activate_overlay(true, "overlay_data");
    var parcel_search_term = document.getElementsByName("address")[0].value;
    var button_value = $("button[type=submit][clicked=true]").val();
    $.ajax({
        url: '/ajax/get_parcels/',
        data: {
            'parcel_search_term': parcel_search_term,
            'search_type': button_value
        },
        dataType: 'json',
        success: handleResponseData
    });
}


$(document).ready(function () {
    //$('table').find('tr:gt(0)').hide();
    $('.dt').find('tbody').toggle();
    $('.dt thead').addClass('hCollapsed');

    mapboxgl.accessToken = 'pk.eyJ1IjoibmVzc2JvdCIsImEiOiJjazU3NnNrb2MwMDcyM2pvNjYzM2hxbDdnIn0.Ip9ledWRI3KfL_FxAykCYA';
    dataMap = instantiateMap('map');
    searchMap = instantiateMap('searchMap', [attachClickSearchToMap]);
    $('#show-map-btn-section').hide();
    $('#show-map-btn-section').on('click', function () {
        $('#searchMap-section').show();
        $('#show-map-btn-section').hide();
    })

    $("#no_results").hide();
    $("#one_result").hide();

    $("form").submit(function (e) {
        refresh_parcel();
        e.preventDefault(); // Don't submit the form.
    });

    $("form").submit(function () {
        var val = $("button[type=submit][clicked=true]").val();
    });
    $("form button[type=submit]").click(function () {
        $("button[type=submit]", $(this).parents("form")).removeAttr("clicked");
        $(this).attr("clicked", "true");
    });

});

//$("thead").find("th").on("click", function() {
$("thead").on("click", function () {                  // When thead is clicked,
    $(this).closest("table").find("tbody").toggle(); // collapse the table.
    if ($(this).hasClass('hCollapsed')) {
        $(this).removeClass('hCollapsed').addClass('hExpanded');
    } else {
        $(this).removeClass('hExpanded').addClass('hCollapsed');
    }
});