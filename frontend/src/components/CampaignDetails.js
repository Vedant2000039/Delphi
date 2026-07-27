import React from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useEffect, useState } from "react";
import axios from "axios";
import * as XLSX from "xlsx";
import { saveAs } from "file-saver";
// import { API_BASE_URL } from '../config';
const API_BASE_URL = process.env.REACT_APP_API_DOMAIN;

export default function CampaignDetails() {
    // const { state } = useLocation();
    const { campaignId } = useParams();
    const [companies, setCompanies] = useState([]);
    const [campaignsMap, setCampaignsMap] = useState([]);
    const navigate = useNavigate();
    const [activeTab, setActiveTab] = useState('companies');
    const [isEncrypted, setIsEncrypted] = useState(false);
    const [qualifiedCompanies, setQualifiedCompanies] = useState([]); // New state for qualified companies
    const [stats, setStats] = useState([]);
    const [showRevenue, setShowRevenue] = useState(false);

    const fetchCompanyList = async (campaignId) => {
        try {
            const response = await axios.get(`${API_BASE_URL}/get_company_by_campaign_id`, {
                params: {
                    Campaign_id: campaignId,
                },
            });
            const companies = Array.isArray(response.data.companies)
                ? response.data.companies
                : [];

            const card_data = Array.isArray(response.data.card_data)
                ? response.data.card_data
                : [];

            // console.log("Fetched companies:", card_data); // Debugging line

            const qualifiedCompanies = companies.filter(company => company.SMTP_Qualified_Count > 0).sort((a, b) => b.SMTP_Qualified_Count - a.SMTP_Qualified_Count);

            // console.log("Qualified companies:", qualifiedCompanies);

            companies.forEach((item) => {
                setCampaignsMap({
                    id: item.Order_key_id,
                    title: item.Campaign_name,
                    client: item.Client_name,
                    code: item.Order_id
                });
            });

            // console.log(" card data:", companies); // Debugging line

            setQualifiedCompanies(qualifiedCompanies);
            setCompanies(companies); // Adjust the state name if needed

            setStats(card_data.map(item => {
                if (item.label === "Projected Revenue") {
                    return {
                        ...item,
                        encryptedValue: item.value,
                        decryptedValue: "", // To be decrypted on toggle
                        value: "**********", // Default hidden state
                    };
                }
                return item;
            }));
            // setStats(card_data);

        } catch (error) {
            console.error("Error fetching campaigns:", error);
        }
    };

    const decryptValue = (encrypted) => {
        try {
            return "$" + parseFloat(atob(encrypted)).toLocaleString("en-IN", {
                minimumFractionDigits: 2,
                maximumFractionDigits: 2
            });
        } catch (e) {
            return "$0.00";
        }
    };


    const handleToggleRevenue = async () => {
        if (!showRevenue) {
            // 1. Decrypt Projected Revenue
            try {
                const updatedStats = await Promise.all(stats.map(async item => {
                    if (item.label === "Projected Revenue" && item.encryptedValue) {
                        const res = await axios.post(`${API_BASE_URL}/decrypt_revenue`, {
                            encrypted_value: item.encryptedValue,
                        });

                        return {
                            ...item,
                            decryptedValue: res.data.value,
                            value: res.data.value,
                        };
                    }
                    return item;
                }));
                setStats(updatedStats);
            } catch (error) {
                console.error("Error decrypting Projected Revenue:", error);
            }

            // 2. Decrypt Price, and restore Revenue from OriginalRevenue
            try {
                const updatedCompanies = await Promise.all(
                    qualifiedCompanies.map(async (account) => {
                        let decryptedVal = null;

                        // Decrypt price if it exists
                        if (account.Price) {
                            try {

                                const res = await axios.post(`${API_BASE_URL}/decrypt_revenue`, {
                                    encrypted_value: String(account.Price),
                                });

                                decryptedVal = res.data?.value;
                                // console.log("Decrypted response:", res.data);
                                // console.log(`Decrypted Price for ${account.Company_name}:`, decryptedVal);

                                // decryptedPrice = decryptedVal ? parseFloat(decryptedVal) : null;
                            } catch (err) {
                                console.error(`Failed to decrypt Price for ${account.Company_name}:`, err);
                            }
                        }

                        return {
                            ...account,
                            DecryptedPrice: decryptedVal,
                            Revenue: account.OriginalRevenue ?? account.Revenue, // restore from backup if needed
                            OriginalRevenue: account.OriginalRevenue ?? account.Revenue, // set backup if not already
                        };
                    })
                );
                // console.log("Decrypted qualified companies:", updatedCompanies);

                setQualifiedCompanies(updatedCompanies);
            } catch (error) {
                console.error("Error decrypting company Prices:", error);
            }

            setShowRevenue(true);
        } else {
            // Mask Projected Revenue
            setStats(prevStats =>
                prevStats.map(item => {
                    if (item.label === "Projected Revenue") {
                        return {
                            ...item,
                            value: "**********",
                        };
                    }
                    return item;
                })
            );

            // Mask Price and Revenue
            setQualifiedCompanies(prevCompanies =>
                prevCompanies.map(account => ({
                    ...account,
                    DecryptedPrice: null,
                    Revenue: null, // will restore from OriginalRevenue on decrypt
                }))
            );

            // console.log("Masked qualified companies:", qualifiedCompanies);

            setShowRevenue(false);
        }
    };


    // const fetchCampaignName = async (campaignId) => {
    //     try {
    //         const response = await axios.get("http://172.16.60.19:8000/get_campaign_by_id", {
    //             params: {
    //                 Campaign_id: campaignId,
    //             },
    //         });
    //         let campaignsArray = response.data.campaigns;

    //         if (!Array.isArray(campaignsArray)) {
    //             campaignsArray = [campaignsArray];
    //         }

    //         campaignsArray.forEach((item) => {
    //             setCampaignsMap({
    //                 id: item.Order_key_id,
    //                 title: item.Campaign_name,
    //                 client: item.Client_name,
    //                 code: item.Order_id
    //             });
    //         });

    //     } catch (error) {
    //         console.error("Error fetching campaigns:", error);
    //     }
    // };

    const generateExcel = () => {
        if (!qualifiedCompanies || qualifiedCompanies.length === 0) {
            alert("No qualified companies to export.");
            return;
        }

        const exportData = qualifiedCompanies.map(company => ({
            "Company Name": company.Company_name,
            "Industry": company.Industry,
            "Country": company.Country,
            "Mail Domain": company.Mail_domain,
            // "Qualified Leads": company.SMTP_Qualified_Count,
            // "Disqualified Leads": company.SMTP_Disqualified_Count,
            // "Pending Leads": company.SMTP_Pending_Count,
        }));

        const worksheet = XLSX.utils.json_to_sheet(exportData);
        const workbook = XLSX.utils.book_new();
        XLSX.utils.book_append_sheet(workbook, worksheet, "Qualified_Accounts");

        const excelBuffer = XLSX.write(workbook, {
            bookType: "xlsx",
            type: "array",
        });

        const fileData = new Blob([excelBuffer], {
            type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        });

        saveAs(fileData, "Qualified_Accounts.xlsx");
    };

    useEffect(() => {
        if (campaignId) {
            // fetchCampaignName(campaignId);
            fetchCompanyList(campaignId);
        }
    }, [campaignId]);
    const capitalizeFirst = (text) => {
        return text ? text.charAt(0).toUpperCase() + text.slice(1) : '';
    };

    return (
        <div className="container-fluid bg-light g-0 vh-500 pt-4">
            <div className="mb-3 p-0 container">
                <button className="btn btn-light border d-flex align-items-center gap-2" onClick={() => navigate("/SuperManagerDashboard")}>
                    <i className="bi bi-arrow-left"></i> Back to Campaigns
                </button>
            </div>
            <div className="card mb-3 container">
                <div className="card-body">
                    <div className="d-flex flex-wrap align-items-center gap-2">
                        {/* Campaign Info */}
                        {campaignsMap && (
                            <div>
                                <h4 className="fw-bold mb-0">{capitalizeFirst(campaignsMap?.title)}</h4>
                                <div className="d-flex align-items-center gap-1 text-secondary">
                                    <span>{campaignsMap.client}</span>
                                    <div style={{ fontSize: "20px", color: "#6c757d", lineHeight: "24px" }}>•</div>
                                    <div>{campaignsMap.code}</div>
                                </div>
                            </div>
                        )}


                        {/* Right: Toggle Encrypt/Decrypt Button */}
                        <div className="ms-auto">
                            <button className={`btn ${isEncrypted ? 'btn-outline-secondary' : 'btn-outline-primary'}`} onClick={handleToggleRevenue}>
                                <i className={`bi ${isEncrypted ? 'bi-unlock' : 'bi-lock'} me-1`}></i>
                                {showRevenue ? "Encrypt" : "Decrypt"}
                            </button>
                        </div>
                    </div>
                </div>
            </div>

            <div className="container my-4 p-0">
                <div className="d-flex justify-content-start align-items-stretch gap-3 flex-nowrap overflow-auto">
                    {stats.map((stat, index) => (
                        <div
                            className="card shadow-sm border-0 position-relative"
                            style={{ minWidth: '251px' }}
                            key={index}
                        >
                            <div className="card-body">
                                <i className={`fa-solid fa-arrow-trend-up position-absolute top-0 end-0 p-2 fs-4 ${stat.color}`}></i>
                                <small className="text-muted">{stat.label}</small>
                                <h5 className={`fw-bold fs-3 ${stat.color}`}>{stat.value}</h5>
                            </div>
                        </div>
                    ))}
                </div>
            </div>



            {/* Companies Section */}
            <div className="container mb-3 p-0 d-flex align-items-center gap-2">
                <button
                    className={`btn ${activeTab === 'companies' ? 'bg_nevy_blue text-white' : 'btn-light text-dark'}`}
                    onClick={() => setActiveTab('companies')}
                >
                    <i className="bi bi-buildings"></i> Targeted Accounts ({companies.length})
                </button>

                <button
                    className={`btn ${activeTab === 'qualified' ? 'bg_nevy_blue text-white' : 'btn-light text-dark'}`}
                    onClick={() => setActiveTab('qualified')}
                >
                    <i className="bi bi-check-circle"></i> Qualified Accounts ({qualifiedCompanies.length})
                </button>
            </div>


            {/* Companies (Account List) Content */}
            {activeTab === 'companies' && (
                <div className="card container">
                    <div className="card-body">
                        <h4 className="mb-3">Targeted Accounts List</h4>

                        <div className="row g-3">
                            {companies.map((a) => (
                                <div key={a.Lead_id} className="col-12 col-md-6 col-xl-4">
                                    <Link
                                        to={`/campaigns/${campaignsMap.id}/companies/${a.Lead_id}`}
                                        state={{ companydetails: a }}
                                        className="text-decoration-none text-dark"
                                    >
                                        <div className="card h-100 hover-shadow">
                                            <div className="card-body">
                                                <h6 className="fw-bold mb-2">{capitalizeFirst(a.Company_name)}</h6>
                                                <div className="d-flex align-items-center gap-2 mb-2">
                                                    <span className="text-secondary">{a.Industry}</span>
                                                    <div style={{ fontSize: "20px", color: "#6c757d", lineHeight: "24px" }}>•</div>
                                                    <span className="text-secondary">{a.Country}</span>
                                                    <div style={{ fontSize: "20px", color: "#6c757d", lineHeight: "24px" }}>•</div>
                                                </div>
                                                <div className="text-secondary mb-3">{a.Mail_domain}</div>
                                                <div className="d-flex align-items-center gap-1 small flex-wrap">
                                                    <span className="text-secondary">
                                                        Lead Score: <span className="text-black">{a.Total_Leads_Scored}</span>
                                                    </span>
                                                    <div className="vr"></div>

                                                    <span className="text-secondary">
                                                        Qualified: <span className="text-success">{a.SMTP_Qualified_Count}</span>
                                                    </span>
                                                    <div className="vr"></div>

                                                    <span className="text-secondary">
                                                        Disqualified: <span className="text-danger">{a.SMTP_Disqualified_Count}</span>
                                                    </span>
                                                    <div className="vr"></div>

                                                    <span className="text-secondary">
                                                        Pending: <span className="text-orange">{a.SMTP_Pending_Count}</span>
                                                    </span>
                                                </div>

                                            </div>
                                        </div>
                                    </Link>
                                </div>
                            ))}

                            {companies.length === 0 && (
                                <div className="alert alert-warning mb-0">No companies found for this campaign.</div>
                            )}
                        </div>
                    </div>
                </div>
            )}

            {/* Tab Content */}
            {/* Qualified Tab Content */}
            {activeTab === 'qualified' && (
                <div className="card container">
                    <div className="card-body">
                        {/* Header row with title and Excel button */}
                        <div className="d-flex justify-content-between align-items-center mb-3">
                            <h4 className="mb-3">Qualified Accounts</h4>
                            <button
                                className="btn bg_nevy_blue text-white"
                                onClick={generateExcel}
                                disabled={qualifiedCompanies.length === 0}
                                title={
                                    qualifiedCompanies.length === 0
                                        ? "No qualified companies to export"
                                        : "Download qualified companies as Excel"
                                }
                            >
                                <i className="bi bi-download me-1"></i> Export TAL
                            </button>
                        </div>

                        {/* Qualified Account List */}
                        <div className="list-group">
                            <div className="table-responsive">
                                {qualifiedCompanies.length > 0 ? (
                                    <table className="table table-hover table-borderless align-middle mb-0 shadow-sm rounded overflow-hidden">
                                        <thead className="table-light text-uppercase text-secondary small">
                                            <tr>
                                                <th style={{ minWidth: '200px' }}>Account Name</th>
                                                <th className="text-end">Lead Score</th>
                                                <th className="text-end text-success">Qualified</th>
                                                <th className="text-end text-danger">Disqualified</th>
                                                <th className="text-end text-warning">Pending</th>
                                                <th className="text-end">CPL</th>
                                                <th className="text-end">Revenue</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {qualifiedCompanies.map((account, index) => (
                                                <tr key={index} className="bg-white border-bottom">
                                                    <td>
                                                        <div className="fw-semibold text-dark">{account.Company_name}</div>
                                                        <div className="text-muted small">
                                                            {account.Industry} • {account.Country} • <span className="text-primary">{account.Mail_domain}</span>
                                                        </div>
                                                    </td>
                                                    <td className="text-end">{account.Total_Leads_Scored || 0}</td>
                                                    <td className="text-end">
                                                        <span className="badge bg-success-subtle text-success fw-semibold">
                                                            {account.SMTP_Qualified_Count || 0}
                                                        </span>
                                                    </td>
                                                    <td className="text-end">
                                                        <span className="badge bg-danger-subtle text-danger fw-semibold">
                                                            {account.SMTP_Disqualified_Count || 0}
                                                        </span>
                                                    </td>
                                                    <td className="text-end">
                                                        <span className="badge bg-warning-subtle text-warning fw-semibold">
                                                            {account.SMTP_Pending_Count || 0}
                                                        </span>
                                                    </td>
                                                    <td className="text-end">
                                                        {showRevenue && account.DecryptedPrice != null ? (
                                                            <span className="text-monospace">{account.DecryptedPrice}</span>
                                                        ) : (
                                                            <span className="text-muted">••••••</span>
                                                        )}
                                                    </td>
                                                    <td className="text-end">
                                                        {showRevenue && account.Revenue != null ? (
                                                            <strong className="text-success text-monospace">
                                                                ${account.Revenue.toLocaleString()}
                                                            </strong>
                                                        ) : (
                                                            <span className="text-muted">••••••</span>
                                                        )}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                ) : (
                                    <div className="alert alert-warning mb-0">No qualified companies found.</div>
                                )}
                            </div>
                        </div>
                    </div>
                </div>

            )}
        </div>
    );
}
