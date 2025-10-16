/**
 * Admin Dashboard Charts JavaScript - Full Implementation
 * Handles: Chart initialization, Data loading, D3.js visualizations, Advanced analytics
 */
// Chart data caching
let currentChartPeriod = "week";
let chartDataCache = {};
let currentBookingChartPeriod = "week";
let bookingChartDataCache = {};
let currentRevenueYear = 2025;
let revenueChartDataCache = {};

// Rate limiting and error tracking
let lastRequestTime = {};
let serverRateLimitHit = {};
const REQUEST_COOLDOWN = 3000; // 3 seconds between requests
const RATE_LIMIT_COOLDOWN = 60000; // 1 minute cooldown after 429 error

function canMakeRequest(endpoint) {
  const now = Date.now();

  // Check if we recently hit a 429 error for this endpoint
  const rateLimitTime = serverRateLimitHit[endpoint] || 0;
  if (now - rateLimitTime < RATE_LIMIT_COOLDOWN) {
    console.log(
      `Server rate limit cooldown active for ${endpoint}. Using fallback data.`
    );
    return false;
  }

  // Check client-side rate limiting
  const lastTime = lastRequestTime[endpoint] || 0;
  if (now - lastTime < REQUEST_COOLDOWN) {
    console.log(
      `Client rate limited: ${endpoint}. Wait ${
        REQUEST_COOLDOWN - (now - lastTime)
      }ms`
    );
    return false;
  }

  lastRequestTime[endpoint] = now;
  return true;
}

function markServerRateLimit(endpoint) {
  serverRateLimitHit[endpoint] = Date.now();
  console.log(
    `Server rate limit hit for ${endpoint}. Will use fallback data for ${
      RATE_LIMIT_COOLDOWN / 1000
    } seconds.`
  );
}

function addDemoDataIndicator(chartId, message) {
  // Remove existing indicator
  const existingIndicator = document.querySelector(
    `#${chartId} .demo-data-indicator`
  );
  if (existingIndicator) {
    existingIndicator.remove();
  }

  // Add new indicator
  const chartElement = document.getElementById(chartId);
  if (chartElement) {
    const indicator = document.createElement("div");
    indicator.className = "demo-data-indicator";
    indicator.style.cssText = `
      position: absolute;
      top: 10px;
      left: 10px;
      background: rgba(255, 193, 7, 0.9);
      color: #856404;
      padding: 4px 8px;
      border-radius: 4px;
      font-size: 11px;
      font-weight: 500;
      z-index: 10;
      border: 1px solid rgba(255, 193, 7, 0.5);
    `;
    indicator.textContent = message;
    chartElement.appendChild(indicator);

    // Auto remove after 10 seconds
    setTimeout(() => {
      if (indicator.parentNode) {
        indicator.remove();
      }
    }, 10000);
  }
}

/**
 * Initialize Line Chart (User Growth)
 */
function initializeLineChart() {
  // Setup dropdown period selection
  const chartPeriodOptions = document.querySelectorAll(".chart-period-option");

  chartPeriodOptions.forEach((option, index) => {
    option.addEventListener("click", function (e) {
      e.preventDefault();

      // Update active state
      document.querySelectorAll(".chart-period-option").forEach((sibling) => {
        sibling.classList.remove("active");
      });
      this.classList.add("active");

      // Update dropdown text
      const periodText = this.getAttribute("data-text");
      const currentPeriodSpan = document.getElementById("currentPeriodText");
      if (currentPeriodSpan) {
        currentPeriodSpan.textContent = periodText;
      }

      // Load new data
      const period = this.getAttribute("data-period");
      currentChartPeriod = period;
      loadLineChartData(period);
    });
  });

  // Load initial data

  loadLineChartData(currentChartPeriod);
}

/**
 * Initialize Booking Chart
 */
function initializeBookingChart() {
  // Setup dropdown period selection
  const bookingPeriodOptions = document.querySelectorAll(
    ".booking-period-option"
  );

  bookingPeriodOptions.forEach((option, index) => {
    option.addEventListener("click", function (e) {
      e.preventDefault();

      // Update active state
      document.querySelectorAll(".booking-period-option").forEach((sibling) => {
        sibling.classList.remove("active");
      });
      this.classList.add("active");

      // Update dropdown text
      const periodText = this.getAttribute("data-text");
      const currentPeriodSpan = document.getElementById(
        "currentBookingPeriodText"
      );
      if (currentPeriodSpan) {
        currentPeriodSpan.textContent = periodText;
      }

      // Load new data
      const period = this.getAttribute("data-period");
      currentBookingChartPeriod = period;
      loadBookingChartData(period);
    });
  });

  // Load initial data

  loadBookingChartData(currentBookingChartPeriod);
}

/**
 * Initialize Revenue Chart
 */
function initializeRevenueChart() {
  // Setup year selection dropdown
  const revenueYearOptions = document.querySelectorAll(".revenue-year-option");

  revenueYearOptions.forEach((option, index) => {
    option.addEventListener("click", function (e) {
      e.preventDefault();

      // Update active state
      document.querySelectorAll(".revenue-year-option").forEach((sibling) => {
        sibling.classList.remove("active");
      });
      this.classList.add("active");

      // Update dropdown text
      const yearText = this.getAttribute("data-text");
      const currentYearSpan = document.getElementById("currentRevenueYearText");
      if (currentYearSpan) {
        currentYearSpan.textContent = yearText;
      }

      // Load new data
      const year = parseInt(this.getAttribute("data-year"));
      currentRevenueYear = year;
      loadRevenueChartData(year);
    });
  });
  // Load initial data
  loadRevenueChartData(currentRevenueYear);
}

/**
 * Load line chart data from API
 */
async function loadLineChartData(period) {
  try {
    // Check cache first
    if (chartDataCache[period]) {
      updateLineChart(chartDataCache[period]);
      return;
    }

    // Check rate limiting
    const endpoint = `user-growth-data/${period}`;
    if (!canMakeRequest(endpoint)) {
      console.log("Request rate limited, using cached data or mock data");
      const mockData = generateMockChartData(period);
      chartDataCache[period] = mockData;
      updateLineChart(mockData);
      return;
    }

    // Show loading state
    showChartLoading(true);

    // Fetch real data from API
    const response = await fetch(`/admin/api/user-growth-data/${period}`);

    // Check if response is ok and content-type is JSON
    if (!response.ok) {
      if (response.status === 429) {
        markServerRateLimit(endpoint);
      }
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const contentType = response.headers.get("content-type");
    if (!contentType || !contentType.includes("application/json")) {
      throw new Error(`Expected JSON but got ${contentType}`);
    }

    const result = await response.json();

    if (result.success) {
      chartDataCache[period] = result.data;
      updateLineChart(result.data);
      if (window.showToast) {
        window.showToast("success", `Đã tải dữ liệu ${getDisplayText(period)}`);
      }
    } else {
      throw new Error(result.error || "Lỗi không xác định");
    }
  } catch (error) {
    console.error("Error loading chart data:", error);

    // Show appropriate message based on error type
    if (window.showToast) {
      if (error.message.includes("429")) {
        window.showToast(
          "warning",
          "Server đang bận, sử dụng dữ liệu demo. Vui lòng thử lại sau 1 phút."
        );
      } else {
        window.showToast("error", "API không khả dụng, sử dụng dữ liệu demo");
      }
    }

    // Fallback to mock data if API fails
    const mockData = generateMockChartData(period);
    chartDataCache[period] = mockData;
    updateLineChart(mockData);

    // Add visual indicator for demo data
    addDemoDataIndicator(
      "userGrowthChart",
      "Dữ liệu demo - API tạm thời không khả dụng"
    );
  } finally {
    showChartLoading(false);
  }
}

/**
 * Load booking chart data from API
 */
async function loadBookingChartData(period) {
  try {
    // Check cache first
    if (bookingChartDataCache[period]) {
      updateBookingChart(bookingChartDataCache[period]);
      return;
    }

    // Check rate limiting
    const endpoint = `booking-stats-data/${period}`;
    if (!canMakeRequest(endpoint)) {
      console.log("Request rate limited, using cached data or mock data");
      const mockData = generateMockBookingChartData(period);
      bookingChartDataCache[period] = mockData;
      updateBookingChart(mockData);
      return;
    }

    // Show loading state
    showBookingChartLoading(true);

    // Fetch real data from API
    const response = await fetch(`/admin/api/booking-stats-data/${period}`);

    // Check if response is ok and content-type is JSON
    if (!response.ok) {
      if (response.status === 429) {
        markServerRateLimit(endpoint);
      }
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const contentType = response.headers.get("content-type");
    if (!contentType || !contentType.includes("application/json")) {
      throw new Error(`Expected JSON but got ${contentType}`);
    }

    const result = await response.json();

    if (result.success) {
      bookingChartDataCache[period] = result.data;
      updateBookingChart(result.data);
      if (window.showToast) {
        window.showToast(
          "success",
          `Đã tải dữ liệu đặt phòng ${getDisplayText(period)}`
        );
      }
    } else {
      throw new Error(result.error || "Lỗi không xác định");
    }
  } catch (error) {
    console.error("Error loading booking chart data:", error);

    // Show appropriate message based on error type
    if (window.showToast) {
      if (error.message.includes("429")) {
        window.showToast(
          "warning",
          "Server đang bận, sử dụng dữ liệu demo. Vui lòng thử lại sau 1 phút."
        );
      } else {
        window.showToast("error", "API không khả dụng, sử dụng dữ liệu demo");
      }
    }

    // Fallback to mock data if API fails
    const mockData = generateMockBookingChartData(period);
    bookingChartDataCache[period] = mockData;
    updateBookingChart(mockData);

    // Add visual indicator for demo data
    addDemoDataIndicator(
      "bookingStatsChart",
      "Dữ liệu demo - API tạm thời không khả dụng"
    );
  } finally {
    showBookingChartLoading(false);
  }
}

/**
 * Load revenue chart data from API
 */
async function loadRevenueChartData(year) {
  try {
    // Check cache first
    if (revenueChartDataCache[year]) {
      updateRevenueChart(revenueChartDataCache[year]);
      return;
    }

    // Show loading state
    showRevenueChartLoading(true);

    // Fetch real data from API
    const response = await fetch(`/admin/api/revenue-stats-data/${year}`);
    const result = await response.json();

    if (result.success) {
      revenueChartDataCache[year] = result.data;
      updateRevenueChart(result.data);
      if (window.showToast) {
        window.showToast("success", `Đã tải dữ liệu doanh thu năm ${year}`);
      }
    } else {
      throw new Error(result.error || "Lỗi không xác định");
    }
  } catch (error) {
    console.error("Error loading revenue chart data:", error);
    if (window.showToast) {
      window.showToast("error", "API không khả dụng, sử dụng dữ liệu demo");
    }

    // Fallback to mock data if API fails
    const mockData = generateMockRevenueChartData(year);
    revenueChartDataCache[year] = mockData;
    updateRevenueChart(mockData);
  } finally {
    showRevenueChartLoading(false);
  }
}

/**
 * Chart loading states
 */
function showChartLoading(isLoading) {
  const chartArea = document.querySelector("#userGrowthChart .chart-area");
  if (!chartArea) return;

  if (isLoading) {
    chartArea.style.opacity = "0.5";
    chartArea.style.pointerEvents = "none";
  } else {
    chartArea.style.opacity = "1";
    chartArea.style.pointerEvents = "auto";
  }
}

function showBookingChartLoading(isLoading) {
  const chartArea = document.querySelector("#bookingStatsChart .chart-area");
  if (!chartArea) return;

  if (isLoading) {
    chartArea.style.opacity = "0.5";
    chartArea.style.pointerEvents = "none";
  } else {
    chartArea.style.opacity = "1";
    chartArea.style.pointerEvents = "auto";
  }
}

function showRevenueChartLoading(isLoading) {
  const chartArea = document.querySelector("#revenueChart .chart-area");
  if (!chartArea) return;

  if (isLoading) {
    chartArea.style.opacity = "0.5";
    chartArea.style.pointerEvents = "none";
  } else {
    chartArea.style.opacity = "1";
    chartArea.style.pointerEvents = "auto";
  }
}

/**
 * Utility functions
 */
function getDisplayText(period) {
  switch (period) {
    case "week":
      return "tuần này";
    case "month":
      return "tháng này";
    case "year":
      return "năm này";
    default:
      return period;
  }
}

function formatCurrency(amount) {
  if (amount >= 1000000) {
    return (amount / 1000000).toFixed(1) + "M";
  } else if (amount >= 1000) {
    return (amount / 1000).toFixed(0) + "k";
  } else {
    return amount.toFixed(0);
  }
}

/**
 * Seeded random number generator for consistent mock data
 */
function seedRandom(seed) {
  let m = 0x80000000; // 2**31
  let a = 1103515245;
  let c = 12345;
  let state = seed ? seed : Math.floor(Math.random() * (m - 1));

  return function () {
    state = (a * state + c) % m;
    return state / (m - 1);
  };
}

/**
 * Mock data generators (fallback)
 */
function generateMockChartData(period) {
  const days = period === "week" ? 7 : period === "month" ? 30 : 52;
  const data = { owners: [], renters: [], labels: [] };

  // Seeded random for consistent data per period
  const seed = period === "week" ? 1234 : period === "month" ? 5678 : 9012;
  let random = seedRandom(seed);

  for (let i = days - 1; i >= 0; i--) {
    const date = new Date();

    if (period === "year") {
      date.setDate(date.getDate() - i * 7);
    } else {
      date.setDate(date.getDate() - i);
    }

    // Generate realistic patterns based on period
    let ownerValue, renterValue;

    if (period === "week") {
      // Weekly pattern: higher on weekends
      const isWeekend = date.getDay() === 0 || date.getDay() === 6;
      ownerValue = Math.floor(random() * 10) + (isWeekend ? 8 : 3);
      renterValue = Math.floor(random() * 15) + (isWeekend ? 12 : 5);
    } else if (period === "month") {
      // Monthly pattern: higher mid-month
      const dayOfMonth = date.getDate();
      const midMonth = dayOfMonth > 10 && dayOfMonth < 20;
      ownerValue = Math.floor(random() * 12) + (midMonth ? 6 : 2);
      renterValue = Math.floor(random() * 18) + (midMonth ? 10 : 3);
    } else {
      // Yearly pattern: higher in summer months
      const month = date.getMonth();
      const isSummer = month >= 5 && month <= 8; // Jun-Sep
      ownerValue = Math.floor(random() * 15) + (isSummer ? 10 : 2);
      renterValue = Math.floor(random() * 25) + (isSummer ? 15 : 3);
    }

    data.owners.push(ownerValue);
    data.renters.push(renterValue);

    if (period === "week") {
      data.labels.push(
        date.toLocaleDateString("vi-VN", { weekday: "short", day: "numeric" })
      );
    } else if (period === "month") {
      data.labels.push(date.getDate().toString());
    } else {
      data.labels.push(date.toLocaleDateString("vi-VN", { month: "short" }));
    }
  }

  return data;
}

function generateMockBookingChartData(period) {
  const days = period === "week" ? 7 : period === "month" ? 30 : 52;
  const data = { hourly: [], nightly: [], labels: [] };

  // Seeded random for consistent data per period
  const seed = period === "week" ? 2345 : period === "month" ? 6789 : 1357;
  let random = seedRandom(seed);

  for (let i = days - 1; i >= 0; i--) {
    const date = new Date();

    if (period === "year") {
      date.setDate(date.getDate() - i * 7);
    } else {
      date.setDate(date.getDate() - i);
    }

    // Generate realistic booking patterns
    let hourlyValue, nightlyValue;

    if (period === "week") {
      // Weekly pattern: higher bookings on weekends
      const isWeekend = date.getDay() === 0 || date.getDay() === 6;
      hourlyValue = Math.floor(random() * 20) + (isWeekend ? 15 : 5);
      nightlyValue = Math.floor(random() * 30) + (isWeekend ? 25 : 8);
    } else if (period === "month") {
      // Monthly pattern: higher bookings mid-month and month-end
      const dayOfMonth = date.getDate();
      const isPeak = (dayOfMonth > 10 && dayOfMonth < 20) || dayOfMonth > 25;
      hourlyValue = Math.floor(random() * 25) + (isPeak ? 12 : 3);
      nightlyValue = Math.floor(random() * 35) + (isPeak ? 20 : 5);
    } else {
      // Yearly pattern: higher bookings in vacation seasons
      const month = date.getMonth();
      const isVacationSeason =
        (month >= 5 && month <= 8) || month >= 11 || month <= 1; // Summer + Winter holidays
      hourlyValue = Math.floor(random() * 30) + (isVacationSeason ? 20 : 5);
      nightlyValue = Math.floor(random() * 50) + (isVacationSeason ? 30 : 8);
    }

    data.hourly.push(hourlyValue);
    data.nightly.push(nightlyValue);

    if (period === "week") {
      data.labels.push(
        date.toLocaleDateString("vi-VN", { weekday: "short", day: "numeric" })
      );
    } else if (period === "month") {
      data.labels.push(date.getDate().toString());
    } else {
      data.labels.push(date.toLocaleDateString("vi-VN", { month: "short" }));
    }
  }

  return data;
}

function generateMockRevenueChartData(year) {
  const data = {
    hourly_revenue: [],
    nightly_revenue: [],
    total_revenue: [],
    labels: [],
    year: year,
  };

  // Seeded random for consistent data per year
  const yearSeed = parseInt(year) || 2025;
  let random = seedRandom(yearSeed);

  const monthNames = [
    "Tháng 1",
    "Tháng 2",
    "Tháng 3",
    "Tháng 4",
    "Tháng 5",
    "Tháng 6",
    "Tháng 7",
    "Tháng 8",
    "Tháng 9",
    "Tháng 10",
    "Tháng 11",
    "Tháng 12",
  ];

  const currentDate = new Date();
  const currentYear = currentDate.getFullYear();
  const currentMonth = currentDate.getMonth() + 1;

  for (let i = 0; i < 12; i++) {
    // Generate realistic seasonal revenue patterns
    const month = i + 1;
    const isSummerSeason = month >= 6 && month <= 8; // Jun-Aug
    const isHolidaySeason = month === 12 || month === 1; // Dec-Jan
    const isHighSeason = isSummerSeason || isHolidaySeason;

    // Base revenue with seasonal multiplier
    const seasonMultiplier = isHighSeason ? 1.5 : 1.0;
    const baseHourly = 800000 + Math.floor(random() * 1200000);
    const baseNightly = 1500000 + Math.floor(random() * 3500000);

    const hourlyRevenue = Math.floor(baseHourly * seasonMultiplier);
    const nightlyRevenue = Math.floor(baseNightly * seasonMultiplier);
    const totalRevenue = hourlyRevenue + nightlyRevenue;

    data.hourly_revenue.push(hourlyRevenue);
    data.nightly_revenue.push(nightlyRevenue);
    data.total_revenue.push(totalRevenue);
    data.labels.push(monthNames[i]);
  }

  data.months_shown = currentMonth;
  data.current_month = currentMonth;

  return data;
}

/**
 * Chart update functions with D3.js - FULL IMPLEMENTATION
 */
function updateLineChart(periodOrData) {
  const chartContainer = document.querySelector("#userGrowthChart .chart-area");
  const xAxisLabels = document.getElementById("xAxisLabels");
  const yAxisLabels = document.querySelector("#userGrowthChart .y-axis-labels");

  if (!chartContainer) return;

  // Fetch real data from API if period string is passed
  if (typeof periodOrData === "string") {
    fetch(`/admin/api/user-growth-data/${periodOrData}`)
      .then((response) => response.json())
      .then((result) => {
        if (result.success && result.data) {
          updateLineChartWithData(result.data);
        } else {
          console.warn("⚠️ API failed, using fallback data:", result.error);
          const fallbackData = generateMockChartData(periodOrData);
          updateLineChartWithData(fallbackData);
        }
      })
      .catch((error) => {
        console.error("❌ API error, using fallback data:", error);
        const fallbackData = generateMockChartData(periodOrData);
        updateLineChartWithData(fallbackData);
      });
    return;
  } else if (periodOrData && typeof periodOrData === "object") {
    updateLineChartWithData(periodOrData);
  } else {
    // Fallback to week data
    const fallbackData = generateMockChartData("week");
    updateLineChartWithData(fallbackData);
  }
}

function updateLineChartWithData(data) {
  const chartContainer = document.querySelector("#userGrowthChart .chart-area");
  const xAxisLabels = document.getElementById("xAxisLabels");
  const yAxisLabels = document.querySelector("#userGrowthChart .y-axis-labels");

  if (!chartContainer || !data) return;

  // Clear existing content
  d3.select("#lineChartSvg").remove();
  if (xAxisLabels) xAxisLabels.innerHTML = "";

  // Handle different data formats (API vs mock)
  const ownersData = data.owners || [];
  const rentersData = data.renters || [];
  const labelsData = data.labels || [];

  // Get container dimensions
  const containerRect = chartContainer.getBoundingClientRect();
  const width = containerRect.width;
  const height = containerRect.height;

  // Find max value for scaling
  const maxOwner = Math.max(...ownersData, 1);
  const maxRenter = Math.max(...rentersData, 1);
  const maxValue = Math.max(maxOwner, maxRenter, 40);

  // Update Y-axis labels
  if (yAxisLabels) {
    const yLabels = yAxisLabels.children;
    for (let i = 0; i < yLabels.length; i++) {
      const value = Math.round(maxValue * (1 - i / (yLabels.length - 1)));
      yLabels[i].textContent = value;
    }
  }

  // Create new SVG with D3
  const svg = d3
    .select(chartContainer)
    .append("svg")
    .attr("id", "lineChartSvg")
    .attr("width", width)
    .attr("height", height)
    .style("position", "absolute")
    .style("top", 0)
    .style("left", 0);

  // Create scales
  const xScale = d3
    .scaleLinear()
    .domain([0, data.owners.length - 1])
    .range([0, width]);

  const yScale = d3.scaleLinear().domain([0, maxValue]).range([height, 0]);

  // Create line generators
  const ownerLine = d3
    .line()
    .x((d, i) => xScale(i))
    .y((d) => yScale(d))
    .curve(d3.curveMonotoneX);

  const renterLine = d3
    .line()
    .x((d, i) => xScale(i))
    .y((d) => yScale(d))
    .curve(d3.curveMonotoneX);

  // Add owner line with animation
  svg
    .append("path")
    .datum(data.owners)
    .attr("fill", "none")
    .attr("stroke", "#dc2626")
    .attr("stroke-width", 3)
    .attr("d", ownerLine)
    .style("opacity", 0)
    .transition()
    .duration(1000)
    .style("opacity", 1);

  // Add renter line with animation
  svg
    .append("path")
    .datum(data.renters)
    .attr("fill", "none")
    .attr("stroke", "#9ed649")
    .attr("stroke-width", 3)
    .attr("d", renterLine)
    .style("opacity", 0)
    .transition()
    .duration(1000)
    .style("opacity", 1);

  // Add owner points
  svg
    .selectAll(".owner-point")
    .data(data.owners)
    .enter()
    .append("circle")
    .attr("class", "owner-point")
    .attr("cx", (d, i) => xScale(i))
    .attr("cy", (d) => yScale(d))
    .attr("r", 0)
    .attr("fill", "#dc2626")
    .attr("stroke", "white")
    .attr("stroke-width", 2)
    .style("cursor", "pointer")
    .on("mouseenter", function (event, d) {
      const index = data.owners.indexOf(d);
      showTooltip(event, `Owner: ${d}`, data.labels[index]);
      d3.select(this).transition().duration(200).attr("r", 6);
    })
    .on("mouseleave", function () {
      hideTooltip();
      d3.select(this).transition().duration(200).attr("r", 4);
    })
    .transition()
    .duration(1000)
    .delay((d, i) => i * 50)
    .attr("r", 4);

  // Add renter points
  svg
    .selectAll(".renter-point")
    .data(data.renters)
    .enter()
    .append("circle")
    .attr("class", "renter-point")
    .attr("cx", (d, i) => xScale(i))
    .attr("cy", (d) => yScale(d))
    .attr("r", 0)
    .attr("fill", "#9ed649")
    .attr("stroke", "white")
    .attr("stroke-width", 2)
    .style("cursor", "pointer")
    .on("mouseenter", function (event, d) {
      const index = data.renters.indexOf(d);
      showTooltip(event, `Renter: ${d}`, data.labels[index]);
      d3.select(this).transition().duration(200).attr("r", 6);
    })
    .on("mouseleave", function () {
      hideTooltip();
      d3.select(this).transition().duration(200).attr("r", 4);
    })
    .transition()
    .duration(1000)
    .delay((d, i) => i * 50 + 100)
    .attr("r", 4);

  // Update X-axis labels
  if (xAxisLabels && labelsData.length > 0) {
    labelsData.forEach((label, index) => {
      if (
        index % Math.ceil(labelsData.length / 7) === 0 ||
        index === labelsData.length - 1
      ) {
        const labelDiv = document.createElement("div");
        labelDiv.textContent = label;
        labelDiv.style.fontSize = "11px";
        labelDiv.style.position = "absolute";
        labelDiv.style.left = `${xScale(index)}px`;
        labelDiv.style.transform = "translateX(-50%)";
        xAxisLabels.appendChild(labelDiv);
      }
    });
  }
}

function updateBookingChart(periodOrData) {
  const chartContainer = document.querySelector(
    "#bookingStatsChart .chart-area"
  );
  const xAxisLabels = document.getElementById("bookingXAxisLabels");
  const yAxisLabels = document.querySelector(
    "#bookingStatsChart .y-axis-labels"
  );

  if (!chartContainer) return;

  // Fetch real data from API if period string is passed
  if (typeof periodOrData === "string") {
    fetch(`/admin/api/booking-stats-data/${periodOrData}`)
      .then((response) => response.json())
      .then((result) => {
        if (result.success && result.data) {
          updateBookingChartWithData(result.data);
        } else {
          console.warn("⚠️ API failed, using fallback data:", result.error);
          const fallbackData = generateMockBookingChartData(periodOrData);
          updateBookingChartWithData(fallbackData);
        }
      })
      .catch((error) => {
        console.error("❌ API error, using fallback data:", error);
        const fallbackData = generateMockBookingChartData(periodOrData);
        updateBookingChartWithData(fallbackData);
      });
    return;
  } else if (periodOrData && typeof periodOrData === "object") {
    updateBookingChartWithData(periodOrData);
  } else {
    // Fallback to week data
    const fallbackData = generateMockBookingChartData("week");
    updateBookingChartWithData(fallbackData);
  }
}

function updateBookingChartWithData(data) {
  const chartContainer = document.querySelector(
    "#bookingStatsChart .chart-area"
  );
  const xAxisLabels = document.getElementById("bookingXAxisLabels");
  const yAxisLabels = document.querySelector(
    "#bookingStatsChart .y-axis-labels"
  );

  if (!chartContainer || !data) return;

  // Clear existing content
  d3.select("#bookingLineChartSvg").remove();
  if (xAxisLabels) xAxisLabels.innerHTML = "";

  // Handle different data formats (API vs mock)
  const hourlyData = data.hourly || [];
  const nightlyData = data.nightly || [];
  const labelsData = data.labels || [];

  // Get container dimensions
  const containerRect = chartContainer.getBoundingClientRect();
  const width = containerRect.width;
  const height = containerRect.height;

  // Find max value for scaling
  const maxHourly = Math.max(...hourlyData, 1);
  const maxNightly = Math.max(...nightlyData, 1);
  const maxValue = Math.max(maxHourly, maxNightly, 100);

  // Update Y-axis labels
  if (yAxisLabels) {
    const yLabels = yAxisLabels.children;
    for (let i = 0; i < yLabels.length; i++) {
      const value = Math.round(maxValue * (1 - i / (yLabels.length - 1)));
      yLabels[i].textContent = value;
    }
  }

  // Create new SVG with D3
  const svg = d3
    .select(chartContainer)
    .append("svg")
    .attr("id", "bookingLineChartSvg")
    .attr("width", width)
    .attr("height", height)
    .style("position", "absolute")
    .style("top", 0)
    .style("left", 0);

  // Create scales
  const xScale = d3
    .scaleLinear()
    .domain([0, data.hourly.length - 1])
    .range([0, width]);

  const yScale = d3.scaleLinear().domain([0, maxValue]).range([height, 0]);

  // Create line generators
  const hourlyLine = d3
    .line()
    .x((d, i) => xScale(i))
    .y((d) => yScale(d))
    .curve(d3.curveMonotoneX);

  const nightlyLine = d3
    .line()
    .x((d, i) => xScale(i))
    .y((d) => yScale(d))
    .curve(d3.curveMonotoneX);

  // Add hourly line
  svg
    .append("path")
    .datum(data.hourly)
    .attr("fill", "none")
    .attr("stroke", "#f59e0b")
    .attr("stroke-width", 3)
    .attr("d", hourlyLine)
    .style("opacity", 0)
    .transition()
    .duration(1000)
    .style("opacity", 1);

  // Add nightly line
  svg
    .append("path")
    .datum(data.nightly)
    .attr("fill", "none")
    .attr("stroke", "#3b82f6")
    .attr("stroke-width", 3)
    .attr("d", nightlyLine)
    .style("opacity", 0)
    .transition()
    .duration(1000)
    .style("opacity", 1);

  // Add hourly points
  svg
    .selectAll(".hourly-point")
    .data(data.hourly)
    .enter()
    .append("circle")
    .attr("class", "hourly-point")
    .attr("cx", (d, i) => xScale(i))
    .attr("cy", (d) => yScale(d))
    .attr("r", 0)
    .attr("fill", "#f59e0b")
    .attr("stroke", "white")
    .attr("stroke-width", 2)
    .style("cursor", "pointer")
    .on("mouseenter", function (event, d) {
      const index = data.hourly.indexOf(d);
      showTooltip(event, `Theo giờ: ${d}`, data.labels[index]);
      d3.select(this).transition().duration(200).attr("r", 6);
    })
    .on("mouseleave", function () {
      hideTooltip();
      d3.select(this).transition().duration(200).attr("r", 4);
    })
    .transition()
    .duration(1000)
    .delay((d, i) => i * 50)
    .attr("r", 4);

  // Add nightly points
  svg
    .selectAll(".nightly-point")
    .data(data.nightly)
    .enter()
    .append("circle")
    .attr("class", "nightly-point")
    .attr("cx", (d, i) => xScale(i))
    .attr("cy", (d) => yScale(d))
    .attr("r", 0)
    .attr("fill", "#3b82f6")
    .attr("stroke", "white")
    .attr("stroke-width", 2)
    .style("cursor", "pointer")
    .on("mouseenter", function (event, d) {
      const index = data.nightly.indexOf(d);
      showTooltip(event, `Qua đêm: ${d}`, data.labels[index]);
      d3.select(this).transition().duration(200).attr("r", 6);
    })
    .on("mouseleave", function () {
      hideTooltip();
      d3.select(this).transition().duration(200).attr("r", 4);
    })
    .transition()
    .duration(1000)
    .delay((d, i) => i * 50 + 100)
    .attr("r", 4);

  // Update X-axis labels
  if (xAxisLabels && labelsData.length > 0) {
    labelsData.forEach((label, index) => {
      if (
        index % Math.ceil(labelsData.length / 7) === 0 ||
        index === labelsData.length - 1
      ) {
        const labelDiv = document.createElement("div");
        labelDiv.textContent = label;
        labelDiv.style.fontSize = "11px";
        labelDiv.style.position = "absolute";
        labelDiv.style.left = `${xScale(index)}px`;
        labelDiv.style.transform = "translateX(-50%)";
        xAxisLabels.appendChild(labelDiv);
      }
    });
  }
}

function updateRevenueChart(yearOrData) {
  const chartContainer = document.querySelector("#revenueChart .chart-area");
  const xAxisLabels = document.getElementById("revenueXAxisLabels");
  const yAxisLabels = document.querySelector("#revenueChart .y-axis-labels");

  if (!chartContainer) return;

  // Fetch real data from API if year string/number is passed
  if (typeof yearOrData === "string" || typeof yearOrData === "number") {
    const year = parseInt(yearOrData) || 2025;

    fetch(`/admin/api/revenue-stats-data/${year}`)
      .then((response) => response.json())
      .then((result) => {
        if (result.success && result.data) {
          updateRevenueChartWithData(result.data);
        } else {
          console.warn("⚠️ API failed, using fallback data:", result.error);
          const fallbackData = generateMockRevenueChartData(year);
          updateRevenueChartWithData(fallbackData);
        }
      })
      .catch((error) => {
        console.error("❌ API error, using fallback data:", error);
        const fallbackData = generateMockRevenueChartData(year);
        updateRevenueChartWithData(fallbackData);
      });
    return;
  } else if (yearOrData && typeof yearOrData === "object") {
    updateRevenueChartWithData(yearOrData);
  } else {
    // Fallback to current year data
    const fallbackData = generateMockRevenueChartData(2025);
    updateRevenueChartWithData(fallbackData);
  }
}

function updateRevenueChartWithData(data) {
  const chartContainer = document.querySelector("#revenueChart .chart-area");
  const xAxisLabels = document.getElementById("revenueXAxisLabels");
  const yAxisLabels = document.querySelector("#revenueChart .y-axis-labels");

  if (!chartContainer || !data) return;

  // Clear existing content
  d3.select(chartContainer).selectAll("svg").remove();
  if (xAxisLabels) xAxisLabels.innerHTML = "";

  // Find max value for scaling
  const maxValue = Math.max(...data.total_revenue, 10000000);

  // Update Y-axis labels
  if (yAxisLabels) {
    const yLabels = yAxisLabels.children;
    for (let i = 0; i < yLabels.length; i++) {
      const value = maxValue * (1 - i / (yLabels.length - 1));
      yLabels[i].textContent = formatCurrency(value);
    }
  }

  // Create all 12 month groups
  const monthNames = [
    "Tháng 1",
    "Tháng 2",
    "Tháng 3",
    "Tháng 4",
    "Tháng 5",
    "Tháng 6",
    "Tháng 7",
    "Tháng 8",
    "Tháng 9",
    "Tháng 10",
    "Tháng 11",
    "Tháng 12",
  ];

  // Ensure data arrays have all 12 months
  while (data.hourly_revenue.length < 12) {
    data.hourly_revenue.push(0);
    data.nightly_revenue.push(0);
    data.total_revenue.push(0);
  }

  // Get container dimensions
  const containerRect = chartContainer.getBoundingClientRect();
  const width = containerRect.width;
  const height = containerRect.height;

  // Create SVG with D3
  const svg = d3
    .select(chartContainer)
    .append("svg")
    .attr("width", width)
    .attr("height", height)
    .style("position", "absolute")
    .style("top", 0)
    .style("left", 0);

  // Create scales
  const xScale = d3
    .scaleBand()
    .domain(monthNames)
    .range([0, width])
    .padding(0.4);

  const yScale = d3.scaleLinear().domain([0, maxValue]).range([height, 0]);

  // Current date to determine which months have data
  const currentDate = new Date();
  const currentMonth = currentDate.getMonth() + 1;

  // Define gradients for bars
  const defs = svg.append("defs");

  const totalGradient = defs
    .append("linearGradient")
    .attr("id", "totalGradient")
    .attr("x1", "0%")
    .attr("y1", "0%")
    .attr("x2", "100%")
    .attr("y2", "100%");
  totalGradient
    .append("stop")
    .attr("offset", "0%")
    .attr("stop-color", "#9ed649");
  totalGradient
    .append("stop")
    .attr("offset", "100%")
    .attr("stop-color", "#8ab82f");

  const nightlyGradient = defs
    .append("linearGradient")
    .attr("id", "nightlyGradient")
    .attr("x1", "0%")
    .attr("y1", "0%")
    .attr("x2", "100%")
    .attr("y2", "100%");
  nightlyGradient
    .append("stop")
    .attr("offset", "0%")
    .attr("stop-color", "#ef4444");
  nightlyGradient
    .append("stop")
    .attr("offset", "100%")
    .attr("stop-color", "#dc2626");

  const hourlyGradient = defs
    .append("linearGradient")
    .attr("id", "hourlyGradient")
    .attr("x1", "0%")
    .attr("y1", "0%")
    .attr("x2", "100%")
    .attr("y2", "100%");
  hourlyGradient
    .append("stop")
    .attr("offset", "0%")
    .attr("stop-color", "#fbbf24");
  hourlyGradient
    .append("stop")
    .attr("offset", "100%")
    .attr("stop-color", "#f59e0b");

  // Create bar groups for each month
  const barGroups = svg
    .selectAll(".bar-group")
    .data(monthNames)
    .enter()
    .append("g")
    .attr("class", "bar-group")
    .attr(
      "transform",
      (d) => `translate(${xScale(d) + xScale.bandwidth() / 2}, 0)`
    );

  // Add bars for each month
  monthNames.forEach((month, index) => {
    const monthNumber = index + 1;
    const hasData =
      data.year !== 2025 || (data.year === 2025 && monthNumber <= currentMonth);

    if (hasData) {
      const totalRevenue = data.total_revenue[index];
      const hourlyRevenue = data.hourly_revenue[index];
      const nightlyRevenue = data.nightly_revenue[index];

      const barGroup = barGroups.filter((d) => d === month);
      const barWidth = 30;
      const halfBarWidth = barWidth / 2;

      // Total revenue bar (green, background)
      barGroup
        .append("rect")
        .attr("class", "total-bar")
        .attr("x", -halfBarWidth)
        .attr("y", height)
        .attr("width", barWidth)
        .attr("height", 0)
        .attr("rx", 4)
        .attr("fill", "url(#totalGradient)")
        .style("stroke", "#7cb518")
        .style("stroke-width", 2)
        .style("cursor", "pointer")
        .on("mouseenter", function (event) {
          showTooltip(
            event,
            `Tổng doanh thu: ${formatCurrency(totalRevenue)} VND`,
            month
          );
          d3.select(this).style("filter", "brightness(1.1)");
        })
        .on("mouseleave", function () {
          hideTooltip();
          d3.select(this).style("filter", "brightness(1)");
        })
        .transition()
        .duration(1000)
        .delay(index * 100)
        .attr("y", yScale(totalRevenue))
        .attr("height", height - yScale(totalRevenue));

      // Nightly revenue bar (red, middle)
      const visibleNightlyHeight =
        nightlyRevenue > 0 ? Math.max(height - yScale(nightlyRevenue), 5) : 0;

      barGroup
        .append("rect")
        .attr("class", "nightly-bar")
        .attr("x", -halfBarWidth)
        .attr("y", height)
        .attr("width", barWidth)
        .attr("height", 0)
        .attr("rx", 4)
        .attr("fill", "url(#nightlyGradient)")
        .style("stroke", "#dc2626")
        .style("stroke-width", 2)
        .style("cursor", "pointer")
        .on("mouseenter", function (event) {
          showTooltip(
            event,
            `Qua đêm: ${formatCurrency(nightlyRevenue)} VND`,
            month
          );
          d3.select(this).style("filter", "brightness(1.1)");
        })
        .on("mouseleave", function () {
          hideTooltip();
          d3.select(this).style("filter", "brightness(1)");
        })
        .transition()
        .duration(1000)
        .delay(index * 100 + 100)
        .attr("y", yScale(nightlyRevenue))
        .attr("height", visibleNightlyHeight);

      // Hourly revenue bar (yellow, front)
      const visibleHourlyHeight =
        hourlyRevenue > 0 ? Math.max(height - yScale(hourlyRevenue), 5) : 0;

      barGroup
        .append("rect")
        .attr("class", "hourly-bar")
        .attr("x", -halfBarWidth)
        .attr("y", height)
        .attr("width", barWidth)
        .attr("height", 0)
        .attr("rx", 4)
        .attr("fill", "url(#hourlyGradient)")
        .style("stroke", "#f59e0b")
        .style("stroke-width", 2)
        .style("cursor", "pointer")
        .on("mouseenter", function (event) {
          showTooltip(
            event,
            `Theo giờ: ${formatCurrency(hourlyRevenue)} VND`,
            month
          );
          d3.select(this).style("filter", "brightness(1.1)");
        })
        .on("mouseleave", function () {
          hideTooltip();
          d3.select(this).style("filter", "brightness(1)");
        })
        .transition()
        .duration(1000)
        .delay(index * 100 + 200)
        .attr("y", yScale(hourlyRevenue))
        .attr("height", visibleHourlyHeight);
    } else {
      // Placeholder bars for future months
      const barGroup = barGroups.filter((d) => d === month);

      barGroup
        .append("rect")
        .attr("class", "placeholder-bar")
        .attr("x", -16)
        .attr("y", height - 15)
        .attr("width", 32)
        .attr("height", 15)
        .attr("rx", 4)
        .attr("fill", "#d1d5db")
        .style("stroke", "#9ca3af")
        .style("stroke-width", 1)
        .style("opacity", 0.4)
        .style("cursor", "not-allowed")
        .on("mouseenter", function (event) {
          showTooltip(
            event,
            `Tháng ${monthNames.indexOf(month) + 1}: Chưa có dữ liệu`,
            month
          );
          d3.select(this).style("opacity", 0.6);
        })
        .on("mouseleave", function () {
          hideTooltip();
          d3.select(this).style("opacity", 0.4);
        });
    }
  });

  // Update X-axis labels
  if (xAxisLabels) {
    monthNames.forEach((month, index) => {
      const labelDiv = document.createElement("div");
      labelDiv.textContent = month.replace("Tháng ", "T");
      labelDiv.style.fontSize = "11px";
      labelDiv.style.position = "absolute";
      labelDiv.style.left = `${xScale(month) + xScale.bandwidth() / 2}px`;
      labelDiv.style.transform = "translateX(-50%)";
      labelDiv.style.textAlign = "center";

      const monthNumber = index + 1;
      const hasData =
        data.year !== 2025 ||
        (data.year === 2025 && monthNumber <= currentMonth);

      if (!hasData) {
        labelDiv.style.color = "#9ca3af";
        labelDiv.style.opacity = "0.6";
      } else {
        labelDiv.style.color = "#374151";
        labelDiv.style.opacity = "1";
      }

      xAxisLabels.appendChild(labelDiv);
    });
  }
}

/**
 * Tooltip functions
 */
let tooltip = null;

function showTooltip(event, value, label) {
  hideTooltip();

  tooltip = document.createElement("div");
  tooltip.style.cssText = `
        position: fixed;
        background: rgba(0, 0, 0, 0.8);
        color: white;
        padding: 8px 12px;
        border-radius: 6px;
        font-size: 12px;
        font-weight: 500;
        z-index: 9999;
        pointer-events: none;
        white-space: nowrap;
    `;
  tooltip.innerHTML = `<div>${label}</div><div>${value}</div>`;

  document.body.appendChild(tooltip);

  const rect = tooltip.getBoundingClientRect();
  tooltip.style.left = `${event.clientX - rect.width / 2}px`;
  tooltip.style.top = `${event.clientY - rect.height - 10}px`;
}

function hideTooltip() {
  if (tooltip) {
    document.body.removeChild(tooltip);
    tooltip = null;
  }
}

/**
 * Initialize Charts System
 */
function initializeCharts() {
  // Initialize chart observers for when stats section is visible
  const statsSection = document.getElementById("section-stats");
  if (statsSection) {
    let chartsInitialized = false;

    const initializeChartsOnce = () => {
      if (!chartsInitialized) {
        initializeLineChart();
        initializeBookingChart();
        initializeRevenueChart();
        chartsInitialized = true;
      }
    };

    // Observer for class changes
    const observer = new MutationObserver(function (mutations) {
      mutations.forEach(function (mutation) {
        if (
          mutation.type === "attributes" &&
          mutation.attributeName === "class"
        ) {
          if (statsSection.classList.contains("active")) {
            setTimeout(initializeChartsOnce, 100);
          }
        }
      });
    });

    // Observer for style changes (display property)
    const styleObserver = new MutationObserver(function (mutations) {
      mutations.forEach(function (mutation) {
        if (
          mutation.type === "attributes" &&
          mutation.attributeName === "style"
        ) {
          if (
            statsSection.style.display !== "none" &&
            getComputedStyle(statsSection).display !== "none"
          ) {
            setTimeout(initializeChartsOnce, 100);
          }
        }
      });
    });

    observer.observe(statsSection, { attributes: true });
    styleObserver.observe(statsSection, { attributes: true });

    // Check initial state
    if (
      statsSection.classList.contains("active") ||
      (statsSection.style.display !== "none" &&
        getComputedStyle(statsSection).display !== "none")
    ) {
      setTimeout(initializeChartsOnce, 100);
    }

    // Force initialize after a delay (fallback)
    setTimeout(() => {
      if (!chartsInitialized) {
        initializeChartsOnce();
      }
    }, 1000);
  }
}

// Export functions for global access
window.initializeLineChart = initializeLineChart;
window.initializeBookingChart = initializeBookingChart;
window.initializeRevenueChart = initializeRevenueChart;

// Auto-initialize when DOM is loaded
document.addEventListener("DOMContentLoaded", initializeCharts);
