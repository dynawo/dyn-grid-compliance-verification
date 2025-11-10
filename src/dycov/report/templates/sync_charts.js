// Array with the IDs of all your charts
const chartIdsString = document.body.getAttribute('data-chart-ids');
const charts = chartIdsString.split(',').map(id => id.trim());
let syncing = false;

const chartDivs = charts.map(id => document.getElementById(id));

const relayoutListener = (eventdata, sourceDiv) => {
    // If a synchronization is in progress, ignore new events
    if (syncing) {
        return;
    }

    const isAutoscaleReset = eventdata['xaxis.autorange'] === true || eventdata['xaxis.rangemode'] === 'tozero' || eventdata['xaxis.rangemode'] === 'normal';
    const isXZoomPan = eventdata['xaxis.range[0]'] !== undefined;

    // Ignore events that don't affect the X-axis
    if (!isAutoscaleReset && !isXZoomPan) {
        return;
    }

    // Activate the sync flag and remove listeners to prevent loops
    syncing = true;
    chartDivs.forEach(div => {
        div.removeAllListeners('plotly_relayout');
    });

    const newLayout = {};
    // Force a data redraw with a random revision number
    newLayout.datarevision = Math.random();

    // Logic to handle autoscale and zoom/pan
    if (isAutoscaleReset) {
        newLayout['xaxis.autorange'] = true;
    } else if (isXZoomPan) {
        newLayout['xaxis.range'] = [eventdata['xaxis.range[0]'], eventdata['xaxis.range[1]']];
    }
    
    // Update all charts
    const promises = charts.map(otherChartId => {
        const otherChartDiv = document.getElementById(otherChartId);
        if (otherChartDiv !== sourceDiv) {
            return Plotly.relayout(otherChartDiv, newLayout);
        }
        return Promise.resolve();
    });

    Promise.all(promises)
        .then(() => {
            // Re-enable listeners once all updates are complete
            chartDivs.forEach(div => {
                div.on('plotly_relayout', (e) => relayoutListener(e, div));
            });
            syncing = false;
        })
        .catch(err => console.error("Error during synchronization:", err));
};

// Assign the listener to each chart
chartDivs.forEach(div => {
    div.on('plotly_relayout', (e) => relayoutListener(e, div));
});