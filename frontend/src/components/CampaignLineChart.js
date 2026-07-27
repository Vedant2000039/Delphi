// // Line Chart Version

import React from "react";
import { Line } from "react-chartjs-2";
import {
    Chart as ChartJS,
    LineElement,
    CategoryScale,
    LinearScale,
    PointElement,
    Tooltip,
    Legend,
} from "chart.js";

ChartJS.register(LineElement, CategoryScale, LinearScale, PointElement, Tooltip, Legend);

const CampaignLineChart = ({ data }) => {
    // Transform campaign data into chart-friendly format
    const labels = data.map((item) => item.Campaign_name || "N/A");
    const totalLeads = data.map((item) => item.Total_Leads_Scored || 0);
    const qualifiedLeads = data.map((item) => item.SMTP_Qualified_Count || 0);
    const pendingLeads = data.map((item) => item.SMTP_Pending_Count || 0);
    const disqualifiedLeads = data.map((item) => item.SMTP_Disqualified_Count || 0);

    const chartData = {
        labels,
        datasets: [
            {
                label: "Total Leads Scored",
                data: totalLeads,
                borderColor: "#254982",
                backgroundColor: (context) => {
                    const chart = context.chart;
                    const { ctx, chartArea } = chart;
                    if (!chartArea) return null;
                    const gradient = ctx.createLinearGradient(0, chartArea.bottom, 0, chartArea.top);
                    gradient.addColorStop(0, "rgba(37,73,130,0.05)");
                    gradient.addColorStop(1, "rgba(37,73,130,0.3)");
                    return gradient;
                },
                tension: 0.3,
                fill: true,
                pointRadius: 5,
                pointBackgroundColor: "#254982",
                pointHoverRadius: 7,
                pointHoverBorderColor: "#fff",
            },
            {
                label: "Qualified Leads",
                data: qualifiedLeads,
                borderColor: "#00C851",
                backgroundColor: "rgba(0,200,81,0.15)",
                tension: 0.3,
                fill: true,
                pointRadius: 4,
                pointBackgroundColor: "#00C851",
                pointHoverRadius: 6,
                pointHoverBorderColor: "#fff",
            },
            {
                label: "Pending Leads",
                data: pendingLeads,
                borderColor: "#ffbb33",
                backgroundColor: "rgba(255,187,51,0.15)",
                tension: 0.3,
                fill: true,
                pointRadius: 4,
                pointBackgroundColor: "#ffbb33",
                pointHoverRadius: 6,
                pointHoverBorderColor: "#fff",
            },
            {
                label: "Disqualified Leads",
                data: disqualifiedLeads,
                borderColor: "#ff4444",
                backgroundColor: "rgba(255,68,68,0.15)",
                tension: 0.3,
                fill: true,
                pointRadius: 4,
                pointBackgroundColor: "#ff4444",
                pointHoverRadius: 6,
                pointHoverBorderColor: "#fff",
            },
        ],
    };

    const options = {
        responsive: true,
        maintainAspectRatio: false,
        interaction: { mode: "nearest", intersect: false },
        plugins: {
            legend: {
                position: "top",
                labels: {
                    font: { size: 13, family: "Inter, sans-serif", weight: "600" },
                    usePointStyle: true,
                    padding: 20,
                },
            },
            tooltip: {
                mode: "index",
                intersect: false,
                backgroundColor: "rgba(0,0,0,0.7)",
                titleFont: { size: 14, weight: "bold" },
                bodyFont: { size: 13 },
                padding: 10,
                cornerRadius: 6,
            },
        },
        scales: {
            x: {
                ticks: { autoSkip: true, maxTicksLimit: 6, padding: 15, color: "#555", font: { weight: "500" } },
                grid: { color: "rgba(0,0,0,0.05)" },
            },
            y: {
                beginAtZero: true,
                ticks: { color: "#555", font: { weight: "500" } },
                grid: { color: "rgba(0,0,0,0.05)" },
            },
        },
    };

    return (
        <div
            className="chart-container"
            style={{
                width: "100%",
                height: "450px",
                borderRadius: "15px",
                padding: "25px",
                // background: "#ffffff",
                // boxShadow: "0 10px 25px rgba(0,0,0,0.08)",
                marginBottom: "40px",
            }}
        >
            <h4 className="mb-4 text-center" style={{ color: "#254982", fontWeight: "700" }}>
                Campaign Summary
            </h4>
            <Line data={chartData} options={options} />
        </div>
    );
};

export default CampaignLineChart;


// // Bar Chart Version

// import React from "react";
// import { Bar } from "react-chartjs-2";
// import {
//     Chart as ChartJS,
//     BarElement,
//     CategoryScale,
//     LinearScale,
//     Tooltip,
//     Legend,
// } from "chart.js";

// ChartJS.register(BarElement, CategoryScale, LinearScale, Tooltip, Legend);

// const CampaignBarChart = ({ data }) => {
//     // Transform campaign data into chart-friendly format
//     const labels = data.map((item) => item.Campaign_name || "N/A");
//     const totalLeads = data.map((item) => item.Total_Leads_Scored || 0);
//     const qualifiedLeads = data.map((item) => item.SMTP_Qualified_Count || 0);
//     const pendingLeads = data.map((item) => item.SMTP_Pending_Count || 0);
//     const disqualifiedLeads = data.map((item) => item.SMTP_Disqualified_Count || 0);

//     const chartData = {
//         labels,
//         datasets: [
//             {
//                 label: "Total Leads Scored",
//                 data: totalLeads,
//                 backgroundColor: "#254982",
//             },
//             {
//                 label: "Qualified Leads",
//                 data: qualifiedLeads,
//                 backgroundColor: "#00C851",
//             },
//             {
//                 label: "Pending Leads",
//                 data: pendingLeads,
//                 backgroundColor: "#ffbb33",
//             },
//             {
//                 label: "Disqualified Leads",
//                 data: disqualifiedLeads,
//                 backgroundColor: "#ff4444",
//             },
//         ],
//     };

//     const options = {
//         responsive: true,
//         maintainAspectRatio: false,
//         plugins: {
//             legend: {
//                 position: "top",
//                 labels: {
//                     font: { size: 13, family: "Inter, sans-serif" },
//                     usePointStyle: true,
//                 },
//             },
//             tooltip: {
//                 mode: "index",
//                 intersect: false,
//             },
//         },
//         scales: {
//             x: {
//                 stacked: false, // Change to true for stacked bars
//                 ticks: { autoSkip: false, padding: 10 },
//                 grid: { color: "rgba(0,0,0,0.05)" },
//             },
//             y: {
//                 beginAtZero: true,
//                 grid: { color: "rgba(0,0,0,0.05)" },
//             },
//         },
//     };

//     return (
//         <div
//             className="chart-container"
//             style={{
//                 width: "100%",
//                 height: "400px",
//                 borderRadius: "10px",
//                 marginBottom: "40px",
//             }}
//         >
//             <h4 className="mb-2">Campaign Summary</h4>
//             <Bar data={chartData} options={options} />
//         </div>
//     );
// };

// export default CampaignBarChart;


// // Pie Chart Version
// import React from "react";
// import { Pie } from "react-chartjs-2";
// import {
//     Chart as ChartJS,
//     ArcElement,
//     Tooltip,
//     Legend,
// } from "chart.js";

// ChartJS.register(ArcElement, Tooltip, Legend);

// const CampaignPieChart = ({ data }) => {
//     // Sum up all leads across campaigns
//     const totalLeads = data.reduce((sum, item) => sum + (item.Total_Leads_Scored || 0), 0);
//     const qualifiedLeads = data.reduce((sum, item) => sum + (item.SMTP_Qualified_Count || 0), 0);
//     const pendingLeads = data.reduce((sum, item) => sum + (item.SMTP_Pending_Count || 0), 0);
//     const disqualifiedLeads = data.reduce((sum, item) => sum + (item.SMTP_Disqualified_Count || 0), 0);

//     const chartData = {
//         labels: ["Qualified Leads", "Pending Leads", "Disqualified Leads", "Total Leads Scored"],
//         datasets: [
//             {
//                 data: [qualifiedLeads, pendingLeads, disqualifiedLeads, totalLeads],
//                 backgroundColor: ["#00C851", "#ffbb33", "#ff4444", "#254982"],
//                 hoverOffset: 10,
//             },
//         ],
//     };

//     const options = {
//         responsive: true,
//         plugins: {
//             legend: {
//                 position: "right",
//                 labels: {
//                     font: { size: 13, family: "Inter, sans-serif" },
//                 },
//             },
//             tooltip: {
//                 callbacks: {
//                     label: function (tooltipItem) {
//                         const value = tooltipItem.raw;
//                         return `${tooltipItem.label}: ${value}`;
//                     },
//                 },
//             },
//         },
//     };

//     return (
//         <div
//             className="chart-container"
//             style={{
//                 width: "100%",
//                 maxWidth: "500px",
//                 margin: "0 auto",
//                 height: "400px",
//                 borderRadius: "10px",
//             }}
//         >
//             <h4 className="mb-3 text-center">Campaign Leads Distribution</h4>
//             <Pie data={chartData} options={options} />
//         </div>
//     );
// };

// export default CampaignPieChart;