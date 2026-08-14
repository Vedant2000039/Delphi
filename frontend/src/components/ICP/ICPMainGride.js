// frontend/src/components/ICP/ICPMainGride.js
import React, { useEffect, useState } from "react";
import axios from "axios";
import ICPLeadsTable from "./ICPLeadsTable";
import { getICPQuadrant } from "./icpQuadrant";   

const API_BASE = (process.env.REACT_APP_API_DOMAIN || "http://localhost:8000")
  .replace(/\/$/, "");

export default function ICPMainGride({ filters, refreshKey, pageSize }) {
  const [leads, setLeads] = useState([]);
  const [totalLeads, setTotalLeads] = useState(0);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [page, setPage] = useState(1);

  useEffect(() => setPage(1), [refreshKey]);
  useEffect(() => setPage(1), [pageSize]);
  useEffect(() => setPage(1), [filters]);

  // ----------------------------
  // Fetch Leads
  // ----------------------------
  const fetchLeads = async () => {
    setLoading(true);
    setError("");

    try {
      const params = {
        country_id: filters?.country || null,
        industry_id: filters?.industry || null,
        employee_size_id: filters?.employee_size || null,
        revenue_size_id: filters?.revenue_size || null,
        job_level_id: filters?.job_level || null,
        job_function_id: filters?.job_function || null,

        page,
        page_size: pageSize,
      };

      Object.keys(params).forEach((k) => {
        if (params[k] === null || params[k] === "") delete params[k];
      });

      const res = await axios.get(
        `${API_BASE}/leadscores/scoring/icp/leads`,
        { params }
      );

      
      const enrichedLeads = (res.data.leads || []).map((lead) => {
        const quadrant = getICPQuadrant(
          lead.icp_score,
          lead.propensity_score
        );

        return {
          ...lead,
          recommended_action: quadrant.action,
          quadrant_name: quadrant.quadrant,
        };
      });

      setLeads(enrichedLeads);
      setTotalLeads(res.data.total || 0);
    } catch (err) {
      console.error("ICP Leads API Error:", err);
      setError("Failed to load ICP leads");
    } finally {
      setLoading(false);
    }
  };

  // ----------------------------
  // Load when filters ready
  // ----------------------------
  useEffect(() => {
    if (!filters) return;

    const hasAnyFilter =
      filters?.country ||
      filters?.industry ||
      filters?.employee_size ||
      filters?.revenue_size ||
      filters?.job_level ||
      filters?.job_function;

    if (!hasAnyFilter) return;

    fetchLeads();
  }, [page, refreshKey, pageSize, filters]);

  if (error) {
    return (
      <div className="alert alert-danger m-3">
        <b>Error:</b> {error}
      </div>
    );
  }

  return (
    <div className="card border-0 shadow-sm rounded-4 overflow-hidden">
      <ICPLeadsTable
        leads={leads}
        loading={loading}
        page={page}
        setPage={setPage}
        total={totalLeads}
        pageSize={pageSize}
      />
    </div>
  );
}



