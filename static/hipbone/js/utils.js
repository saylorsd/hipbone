function handleResponseData(data) {
    if (!("reload" in data)) {
        if (data.parcels.length > 0) {
            $("#no_results").hide();
            $("#prop_addr").html(data.parcels[0].prop_addr);
            $("#prop_parcelnum").html(data.parcels[0].prop_parcelnum);
            $("#city_name").html(data.parcels[0].city_name);

            $("#census_tract_number").html(data.parcels[0].census_tract_number);
            $("#latitude").html(data.parcels[0].y_wgs84);
            $("#longitude").html(data.parcels[0].x_wgs84);
            populate_table(data.voters, "#voters-table");
            populate_grouped_table(data.ownership_grouped, "#ownership-table");
            populate_grouped_table(data.demolitions_grouped, "#demolitions-table");
            populate_grouped_table(data.vacancy_grouped, "#vacancy-table");
            populate_grouped_table(data.blight_violations_grouped, "#blight-violations-table");
            populate_grouped_table(data.building_permits_grouped, "#building-permits-table");
            populate_grouped_table(data.parcel_tax_and_values_grouped, "#parcel-tax-and-values-table");
            populate_grouped_table(data.property_sales_grouped, "#property-sales-table");

            populate_table(data.tax_foreclosures, "#tax-foreclosures-table", "center-text");
            var foreclosures_width = Object.keys(data.tax_foreclosures[0]).length; // Works under ES5+-capable browsers.
            $("#tax-foreclosures-table th").attr('colspan', foreclosures_width);

            activate_overlay(false, "overlay_data");
            highlightParcel(dataMap, data.parcels[0].prop_parcelnum, data.parcels[0].x_wgs84, data.parcels[0].y_wgs84);

            $("#one_result").show();
            $('#show-map-btn-section').show();
            $('#searchMap-section').hide();

        } else {
            $("#no_results").show();
            $("#one_result").hide();
            $('#show-map-btn-section').hide();
            $('#searchMap-section').show();
            activate_overlay(false, "overlay_data");
        }
    } else {
        location.reload(true);
    }
}
