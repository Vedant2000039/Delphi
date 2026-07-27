import React, { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import axios from "axios";
// import { API_BASE_URL } from '../config';

const API_BASE_URL = process.env.REACT_APP_API_DOMAIN;

const fallbackCompany = {
  Lead_id: "123",
  Company_name: "Retail Masters",
  Mail_domain: "retailmasters.com",
  Standard_industry_id: "Retail",
  Country_id: "1",
  Order_key_id: "60",
};

export default function CompanyDetails() {
  const navigate = useNavigate();
  const { state } = useLocation();
  const companydetails = state?.companydetails ?? fallbackCompany; // Company object from state or fallback

  const [card_stats, setStats] = useState([]);
  const [showRevenue, setShowRevenue] = useState(false);
  const [isEncrypted, setIsEncrypted] = useState(false);

  // Extract individual fields from company
  const {
    Company_name,
    Mail_domain,
    Standard_industry_id,
    Country_id,
    Order_key_id,
  } = companydetails;

  // Optional: Store companies from API response
  const [company, setCompany] = useState([]);

  const fetchCompanyList = async () => {
    try {
      const response = await axios.get(`${API_BASE_URL}/get_single_company_details`, {
        params: {
          Company_name,
          Domain: Mail_domain,
          Standard_industry_id,
          Country_id,
          Order_key_id,
        },
      });

      const company = Array.isArray(response.data.company) ? response.data.company : [];
      const card_data = Array.isArray(response.data.card_data) ? response.data.card_data : [];

      setStats(
        card_data.map((item) => {
          if (item.label === "Projected Revenue" || item.label === "CPL") {
            return {
              ...item,
              encryptedValue: item.value,
              decryptedValue: "", // Optional, if you want to store decrypted separately
              value: "**********", // Masked by default
            };
          }
          return item;
        })
      );

      setCompany(company);
    } catch (error) {
      console.error("Error fetching company data:", error);
    }
  };

  const handleToggleAllStats = async () => {
    const labels = ["Projected Revenue", "CPL"];
    const areAnyDecrypted = card_stats.some(
      (item) => labels.includes(item.label) && item.value !== "**********"
    );

    if (!areAnyDecrypted) {
      // Decrypt both
      try {
        const updatedStats = await Promise.all(
          card_stats.map(async (item) => {
            if (!labels.includes(item.label)) return item;

            const endpoint =
              item.label === "Projected Revenue" ? "decrypt_price_revenue" : "decrypt_price_cpl";

            const response = await axios.post(`${API_BASE_URL}/${endpoint}`, {
              encrypted_value: item.encryptedValue,
            });

            return {
              ...item,
              value: response.data.value,
            };
          })
        );
        setStats(updatedStats);
        setIsEncrypted(true);
        setShowRevenue(true);
      } catch (error) {
        console.error("Error decrypting stats:", error);
      }
    } else {
      // Mask both
      setStats((prevStats) =>
        prevStats.map((item) => {
          if (labels.includes(item.label)) {
            return {
              ...item,
              value: "**********",
            };
          }
          return item;
        })
      );
      setIsEncrypted(false);
      setShowRevenue(false);
    }
  };

  useEffect(() => {
    fetchCompanyList();
  }, [Company_name, Mail_domain, Standard_industry_id, Country_id, Order_key_id]);

  return (
    <div className="container-fluid bg-light g-0 vh-100 pt-4">
      <div className="mb-3 p-0 container">
        <button className="btn btn-light border d-flex align-items-center gap-2" onClick={() => navigate(-1)}>
          <i className="bi bi-arrow-left"></i> Back
        </button>
      </div>

      <div className="card mb-3 container">
        <div className="card-body">
          <div className="d-flex flex-wrap align-items-center gap-2">
            <div>
              <h4 className="fw-bold mb-1">{companydetails.Company_name}</h4>
              <div className="text-secondary">
                <span>{companydetails.Industry}</span>
                <span style={{ fontSize: "20px", color: "#6c757d", lineHeight: "30px", padding: "5px" }}>
                  •
                </span>
                <span>{companydetails.Mail_domain}</span>
                <span style={{ fontSize: "20px", color: "#6c757d", lineHeight: "30px", padding: "5px" }}>
                  •
                </span>
                <span>{companydetails.Country}</span>
              </div>
            </div>

            <div className="ms-auto">
              <button
                className={`btn ${showRevenue ? "btn-outline-secondary" : "btn-outline-primary"} d-flex align-items-center gap-2`}
                onClick={handleToggleAllStats}
              >
                <i className={`bi ${showRevenue ? "bi-unlock" : "bi-lock"}`}></i>
                {showRevenue ? "Encrypt" : "Decrypt"} Revenue & CPL
              </button>
            </div>
          </div>
        </div>
      </div>

      <div className="container align-items-center mb-3 p-0">
        <div className="container my-4 p-0">
          <div className="d-flex justify-content-start align-items-stretch gap-3 flex-nowrap">
            {card_stats.map((stat, index) => (
              <div className="card shadow-sm border-0 position-relative" style={{ minWidth: "251px" }} key={index}>
                <div className="card-body">
                  <i
                    className={`fa-solid fa-arrow-trend-up position-absolute top-0 end-0 p-2 fs-4 ${stat.color}`}
                  ></i>
                  <small className="text-muted">{stat.label}</small>
                  <h5 className={`fw-bold fs-3 ${stat.color}`}>{stat.value}</h5>
                </div>
              </div>
            ))}
          </div>
        </div>

        <div className="row g-3 mb-3 justify-content-center">
          <div className="col-12">
            <div className="card h-100">
              <div className="card shadow-sm border-0">
                <div className="card-body">
                  <h5 className="fw-bold mb-4">
                    <i className="bi bi-building me-2"></i>
                    Company Information
                  </h5>

                  <div className="row mb-3">
                    <div className="col-6">
                      <div className="text-secondary small mb-1">Company Name</div>
                      <div className="fw-semibold">{companydetails.Company_name}</div>
                    </div>
                    <div className="col-6">
                      <div className="text-secondary small mb-1">Domain</div>
                      <div className="fw-semibold">{companydetails.Mail_domain}</div>
                    </div>
                  </div>

                  <div className="row mb-3">
                    <div className="col-6">
                      <div className="text-secondary small mb-1">Industry</div>
                      <div>
                        <span className="badge text-bg-light text-dark px-2 py-1">
                          {companydetails.Industry}
                        </span>
                      </div>
                    </div>
                    <div className="col-6">
                      <div className="text-secondary small mb-1">Geography</div>
                      <div className="fw-semibold">
                        <i className="bi bi-geo-alt me-1"></i>
                        {companydetails.Country}
                      </div>
                    </div>
                  </div>

                  {companydetails.Account_Manager && (
                    <div className="row">
                      <div className="col-6">
                        <div className="text-secondary small mb-1">Account Manager</div>
                        <div className="fw-semibold">
                          <i className="bi bi-person-badge me-1"></i>
                          {companydetails.Account_Manager}
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}