import { FormEvent, useEffect, useState } from "react";

type EventItem = {
    id: string;
    title: string;
    event_type: string;
    venue: string;
    address: string;
    city: string;
    country: string;
    start_at: string;
    end_at: string;
    capacity: number;
    description: string;
    status: string;
    organizer_id: string;
    latitude: string | null;
    longitude: string | null;
    media: string[];
    ticket_types: { id: string; name: string; price: string; available: number }[];
};

type EventListResponse = { items: EventItem[]; total: number; page: number; page_size: number };

type User = { username: string; role: string; status: string };
type AdminUser = User & { id: string; email: string; first_name: string; last_name: string };
type AdminUserDetail = AdminUser & { phone: string; address: string; city: string; country: string; tax_id: string; created_at: string };
type Recommendation = { event_id: string; title: string; score: number; reason: string };
type OrganizerBooking = {
    id: string;
    attendee_id: string;
    attendee_username: string;
    ticket_type_id: string;
    ticket_type_name: string;
    number_of_tickets: number;
    total_cost: string;
    status: string;
    created_at: string;
};
type Message = {
    id: string;
    event_id: string;
    event_title: string;
    sender_id: string;
    sender_username: string;
    recipient_id: string;
    recipient_username: string;
    body: string;
    is_read: boolean;
    created_at: string;
};
type TicketRow = { name: string; price: string; quantity: string };

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000/api";

function toDateTimeLocal(value: string) {
    return value.slice(0, 16);
}

export function App() {
    const [events, setEvents] = useState<EventItem[]>([]);
    const [search, setSearch] = useState("");
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");
    const [user, setUser] = useState<User | null>(null);
    const [authMode, setAuthMode] = useState<"login" | "register" | null>(null);
    const [authMessage, setAuthMessage] = useState("");
    const [authError, setAuthError] = useState("");
    const [selectedEvent, setSelectedEvent] = useState<EventItem | null>(null);
    const [selectedTicket, setSelectedTicket] = useState("");
    const [ticketQuantity, setTicketQuantity] = useState(1);
    const [bookingMessage, setBookingMessage] = useState("");
    const [bookingError, setBookingError] = useState("");
    const [dashboardOpen, setDashboardOpen] = useState(false);
    const [managedUsers, setManagedUsers] = useState<AdminUser[]>([]);
    const [ownedEvents, setOwnedEvents] = useState<EventItem[]>([]);
    const [dashboardError, setDashboardError] = useState("");
    const [recommendations, setRecommendations] = useState<Recommendation[]>([]);
    const [messagesOpen, setMessagesOpen] = useState(false);
    const [messagesTab, setMessagesTab] = useState<"inbox" | "sent">("inbox");
    const [inboxMessages, setInboxMessages] = useState<Message[]>([]);
    const [sentMessages, setSentMessages] = useState<Message[]>([]);
    const [unreadCount, setUnreadCount] = useState(0);
    const [messagesError, setMessagesError] = useState("");
    const [createEventOpen, setCreateEventOpen] = useState(false);
    const [ticketRows, setTicketRows] = useState<TicketRow[]>([{ name: "", price: "", quantity: "" }]);
    const [createEventError, setCreateEventError] = useState("");
    const [createEventMessage, setCreateEventMessage] = useState("");
    const [contactBody, setContactBody] = useState("");
    const [contactMessage, setContactMessage] = useState("");
    const [editingEvent, setEditingEvent] = useState<EventItem | null>(null);
    const [editEventError, setEditEventError] = useState("");
    const [editEventMessage, setEditEventMessage] = useState("");
    const [categoryFilter, setCategoryFilter] = useState("");
    const [dateFrom, setDateFrom] = useState("");
    const [dateTo, setDateTo] = useState("");
    const [maxPrice, setMaxPrice] = useState("");
    const [locationFilter, setLocationFilter] = useState("");
    const [page, setPage] = useState(1);
    const [totalEvents, setTotalEvents] = useState(0);
    const pageSize = 6;
    const [userStatusFilter, setUserStatusFilter] = useState<"pending" | "approved" | "rejected" | "all">("pending");
    const [selectedUserDetail, setSelectedUserDetail] = useState<AdminUserDetail | null>(null);
    const [viewingBookingsEvent, setViewingBookingsEvent] = useState<EventItem | null>(null);
    const [eventBookings, setEventBookings] = useState<OrganizerBooking[]>([]);
    const [eventBookingsError, setEventBookingsError] = useState("");
    const [mediaUrlsText, setMediaUrlsText] = useState("");
    const [bookingConfirmStep, setBookingConfirmStep] = useState(false);

    useEffect(() => {
        const token = localStorage.getItem("access_token");
        if (!token) return;
        fetch(`${API_URL}/auth/me`, { headers: { Authorization: `Bearer ${token}` } })
            .then((response) => response.ok ? response.json() : Promise.reject())
            .then((loadedUser) => { setUser(loadedUser); void loadUnreadCount(token); })
            .catch(() => localStorage.removeItem("access_token"));
    }, []);

    async function loadUnreadCount(token: string) {
        const response = await fetch(`${API_URL}/messages/unread-count`, { headers: { Authorization: `Bearer ${token}` } });
        if (response.ok) setUnreadCount((await response.json()).count);
    }

    async function loadEvents(targetPage = page) {
        setLoading(true);
        setError("");
        try {
            const params = new URLSearchParams();
            if (search) params.set("search", search);
            if (categoryFilter) params.set("category", categoryFilter);
            if (locationFilter) params.set("location", locationFilter);
            if (dateFrom) params.set("date_from", dateFrom);
            if (dateTo) params.set("date_to", dateTo);
            if (maxPrice) params.set("max_price", maxPrice);
            params.set("page", String(targetPage));
            params.set("page_size", String(pageSize));
            const response = await fetch(`${API_URL}/events?${params.toString()}`);
            if (!response.ok) throw new Error("Unable to load events");
            const body: EventListResponse = await response.json();
            setEvents(body.items);
            setTotalEvents(body.total);
            setPage(body.page);
        } catch (requestError) {
            setError(requestError instanceof Error ? requestError.message : "Unable to load events");
        } finally {
            setLoading(false);
        }
    }

    useEffect(() => {
        void loadEvents(1);
    }, []);

    function submitSearch(event: FormEvent) {
        event.preventDefault();
        void loadEvents(1);
    }

    async function submitAuth(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setAuthError("");
        setAuthMessage("");
        const form = new FormData(event.currentTarget);
        const isRegister = authMode === "register";
        const payload = isRegister ? {
            username: form.get("username"), password: form.get("password"), password_confirmation: form.get("password_confirmation"), first_name: form.get("first_name"),
            last_name: form.get("last_name"), email: form.get("email"), phone: form.get("phone"),
            address: form.get("address"), city: form.get("city"), country: form.get("country"),
            tax_id: form.get("tax_id"), requested_role: form.get("requested_role"),
        } : { username: form.get("username"), password: form.get("password") };
        try {
            const response = await fetch(`${API_URL}/auth/${isRegister ? "register" : "login"}`, {
                method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
            });
            const body = await response.json();
            if (!response.ok) throw new Error(body.detail ?? "Authentication failed");
            if (isRegister) {
                setAuthMessage("Your registration is pending administrator approval.");
            } else {
                localStorage.setItem("access_token", body.access_token);
                const meResponse = await fetch(`${API_URL}/auth/me`, { headers: { Authorization: `Bearer ${body.access_token}` } });
                setUser(await meResponse.json());
                void loadUnreadCount(body.access_token);
                setAuthMode(null);
            }
        } catch (requestError) {
            setAuthError(requestError instanceof Error ? requestError.message : "Authentication failed");
        }
    }

    function signOut() {
        localStorage.removeItem("access_token");
        setUser(null);
        setUnreadCount(0);
    }

    async function openMessages(tab: "inbox" | "sent" = messagesTab) {
        setMessagesTab(tab);
        setMessagesError("");
        setMessagesOpen(true);
        const token = localStorage.getItem("access_token");
        const response = await fetch(`${API_URL}/messages/${tab}`, { headers: { Authorization: `Bearer ${token}` } });
        if (!response.ok) { setMessagesError("Unable to load messages"); return; }
        const body = await response.json();
        if (tab === "inbox") { setInboxMessages(body); void loadUnreadCount(token ?? ""); }
        else setSentMessages(body);
    }

    async function deleteMessage(messageId: string, tab: "inbox" | "sent") {
        const token = localStorage.getItem("access_token");
        const response = await fetch(`${API_URL}/messages/${messageId}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } });
        if (response.ok) {
            if (tab === "inbox") setInboxMessages((current) => current.filter((item) => item.id !== messageId));
            else setSentMessages((current) => current.filter((item) => item.id !== messageId));
        }
    }

    async function sendContactMessage(event: FormEvent) {
        event.preventDefault();
        if (!selectedEvent || !user) return;
        setContactMessage("");
        const token = localStorage.getItem("access_token");
        const response = await fetch(`${API_URL}/messages`, {
            method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
            body: JSON.stringify({ event_id: selectedEvent.id, recipient_id: selectedEvent.organizer_id, body: contactBody }),
        });
        if (response.ok) { setContactMessage("Message sent to the organizer."); setContactBody(""); }
        else setContactMessage("Unable to send message. A booking is required first.");
    }

    function updateTicketRow(index: number, field: keyof TicketRow, value: string) {
        setTicketRows((current) => current.map((row, rowIndex) => rowIndex === index ? { ...row, [field]: value } : row));
    }

    function openEditEvent(item: EventItem) {
        setEditingEvent(item);
        setEditEventError("");
        setEditEventMessage("");
        setMediaUrlsText(item.media.join("\n"));
    }

    async function submitEditEvent(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        if (!editingEvent) return;
        setEditEventError("");
        setEditEventMessage("");
        const form = new FormData(event.currentTarget);
        const token = localStorage.getItem("access_token");
        const payload = {
            title: form.get("title"),
            event_type: form.get("event_type"),
            venue: form.get("venue"),
            address: form.get("address"),
            city: form.get("city"),
            country: form.get("country"),
            latitude: form.get("latitude") ? Number(form.get("latitude")) : null,
            longitude: form.get("longitude") ? Number(form.get("longitude")) : null,
            start_at: form.get("start_at"),
            end_at: form.get("end_at"),
            description: form.get("description"),
            media: mediaUrlsText.split("\n").map((value) => value.trim()).filter(Boolean),
        };
        const response = await fetch(`${API_URL}/events/${editingEvent.id}`, {
            method: "PATCH", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
            body: JSON.stringify(payload),
        });
        const body = await response.json();
        if (!response.ok) { setEditEventError(body.detail ?? "Unable to update event"); return; }
        setEditEventMessage("Event updated.");
        setOwnedEvents((current) => current.map((item) => item.id === body.id ? body : item));
    }

    async function submitCreateEvent(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setCreateEventError("");
        setCreateEventMessage("");
        const form = new FormData(event.currentTarget);
        const token = localStorage.getItem("access_token");
        const payload = {
            title: form.get("title"),
            categories: String(form.get("categories") ?? "").split(",").map((value) => value.trim()).filter(Boolean),
            event_type: form.get("event_type"),
            venue: form.get("venue"),
            address: form.get("address"),
            city: form.get("city"),
            country: form.get("country"),
            latitude: form.get("latitude") ? Number(form.get("latitude")) : null,
            longitude: form.get("longitude") ? Number(form.get("longitude")) : null,
            start_at: form.get("start_at"),
            end_at: form.get("end_at"),
            capacity: Number(form.get("capacity")),
            description: form.get("description"),
            ticket_types: ticketRows.filter((row) => row.name && row.price && row.quantity).map((row) => ({ name: row.name, price: Number(row.price), quantity: Number(row.quantity) })),
            media: mediaUrlsText.split("\n").map((value) => value.trim()).filter(Boolean),
        };
        const response = await fetch(`${API_URL}/events`, {
            method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
            body: JSON.stringify(payload),
        });
        const body = await response.json();
        if (!response.ok) { setCreateEventError(body.detail ?? "Unable to create event"); return; }
        setCreateEventMessage("Event created as a draft. Publish it from your dashboard.");
        setTicketRows([{ name: "", price: "", quantity: "" }]);
        setMediaUrlsText("");
        setOwnedEvents((current) => [body, ...current]);
    }

    async function openDashboard() {
        setDashboardError("");
        setDashboardOpen(true);
        const token = localStorage.getItem("access_token");
        const headers = { Authorization: `Bearer ${token}` };
        try {
            if (user?.role === "admin") {
                await loadUsers(userStatusFilter);
            }
            if (user?.role === "organizer") {
                const response = await fetch(`${API_URL}/events/organizer/mine`, { headers });
                if (!response.ok) throw new Error("Unable to load your events");
                setOwnedEvents(await response.json());
            }
            if (user?.role === "participant") {
                const response = await fetch(`${API_URL}/recommendations`, { headers });
                if (!response.ok) throw new Error("Unable to load recommendations");
                setRecommendations(await response.json());
            }
        } catch (requestError) {
            setDashboardError(requestError instanceof Error ? requestError.message : "Unable to load dashboard");
        }
    }

    async function loadUsers(filter: "pending" | "approved" | "rejected" | "all") {
        setUserStatusFilter(filter);
        const token = localStorage.getItem("access_token");
        const query = filter === "all" ? "" : `?status=${filter}`;
        const response = await fetch(`${API_URL}/admin/users${query}`, { headers: { Authorization: `Bearer ${token}` } });
        if (!response.ok) { setDashboardError("Unable to load users"); return; }
        setManagedUsers(await response.json());
    }

    async function openUserDetail(userId: string) {
        const token = localStorage.getItem("access_token");
        const response = await fetch(`${API_URL}/admin/users/${userId}`, { headers: { Authorization: `Bearer ${token}` } });
        if (response.ok) setSelectedUserDetail(await response.json());
    }

    async function reviewUser(userId: string, action: "approve" | "reject") {
        const token = localStorage.getItem("access_token");
        const response = await fetch(`${API_URL}/admin/users/${userId}/${action}`, { method: "POST", headers: { Authorization: `Bearer ${token}` } });
        if (response.ok) {
            const updated = await response.json();
            setManagedUsers((current) => userStatusFilter === "all" ? current.map((item) => item.id === userId ? updated : item) : current.filter((item) => item.id !== userId));
            setSelectedUserDetail((current) => current && current.id === userId ? updated : current);
        }
    }

    async function viewEventBookings(item: EventItem) {
        setViewingBookingsEvent(item);
        setEventBookingsError("");
        const token = localStorage.getItem("access_token");
        const response = await fetch(`${API_URL}/events/${item.id}/bookings`, { headers: { Authorization: `Bearer ${token}` } });
        if (!response.ok) { setEventBookingsError("Unable to load bookings"); return; }
        setEventBookings(await response.json());
    }

    async function downloadExport(kind: "xml" | "json") {
        const token = localStorage.getItem("access_token");
        const response = await fetch(`${API_URL}/admin/exports/events.${kind}`, { headers: { Authorization: `Bearer ${token}` } });
        if (!response.ok) { setDashboardError("Unable to export events"); return; }
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `events.${kind}`;
        link.click();
        URL.revokeObjectURL(url);
    }

    async function updateOwnedEvent(eventId: string, action: "publish" | "cancel" | "delete") {
        const token = localStorage.getItem("access_token");
        const response = await fetch(`${API_URL}/events/${eventId}${action === "delete" ? "" : `/${action}`}`, { method: action === "delete" ? "DELETE" : "POST", headers: { Authorization: `Bearer ${token}` } });
        if (response.ok) {
            if (action === "delete") setOwnedEvents((current) => current.filter((item) => item.id !== eventId));
            else setOwnedEvents((current) => current.map((item) => item.id === eventId ? { ...item, status: action === "publish" ? "published" : "cancelled" } : item));
        }
    }

    function openEvent(item: EventItem) {
        setSelectedEvent(item);
        setSelectedTicket(item.ticket_types[0]?.id ?? "");
        setTicketQuantity(1);
        setBookingMessage("");
        setBookingError("");
        setContactBody("");
        setContactMessage("");
        setBookingConfirmStep(false);
        const token = localStorage.getItem("access_token");
        if (token) void fetch(`${API_URL}/events/${item.id}/views`, { method: "POST", headers: { Authorization: `Bearer ${token}` } });
    }

    async function submitBooking(event: FormEvent) {
        event.preventDefault();
        if (!selectedEvent || !user) return;
        if (!bookingConfirmStep) { setBookingConfirmStep(true); return; }
        setBookingError("");
        setBookingMessage("");
        const token = localStorage.getItem("access_token");
        const response = await fetch(`${API_URL}/events/${selectedEvent.id}/bookings`, {
            method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
            body: JSON.stringify({ ticket_type_id: selectedTicket, number_of_tickets: ticketQuantity }),
        });
        const body = await response.json();
        if (!response.ok) setBookingError(body.detail ?? "Booking failed");
        else setBookingMessage(`Booking confirmed for ${body.number_of_tickets} ticket(s).`);
        setBookingConfirmStep(false);
    }

    return (
        <main className="app-shell">
            <nav className="topbar">
                <a className="brand" href="/">GATHER<span>.</span></a>
                <div className="nav-actions">
                    {user ? <><span className="user-label">{user.username} · {user.role}</span><button className="text-button" type="button" onClick={() => openMessages("inbox")}>Messages{unreadCount > 0 && <span className="unread-badge">{unreadCount}</span>}</button><button className="text-button" type="button" onClick={openDashboard}>Dashboard</button><button className="text-button" type="button" onClick={signOut}>Sign out</button></> : <><button className="text-button" type="button" onClick={() => setAuthMode("login")}>Sign in</button><button className="primary-button" type="button" onClick={() => setAuthMode("register")}>Create account</button></>}
                </div>
            </nav>

            <section className="hero">
                <p className="eyebrow">EVENTS, MADE HUMAN</p>
                <h1>Find your next<br /><em>good reason</em> to go out.</h1>
                <p className="hero-copy">Concerts, talks, performances and gatherings worth making room for.</p>
                <form className="search-bar" onSubmit={submitSearch}>
                    <label htmlFor="event-search">Search events</label>
                    <input id="event-search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Try “music”, “Athens”..." />
                    <button className="search-button" type="submit">Search</button>
                </form>
                <div className="filter-bar">
                    <label>Category<input value={categoryFilter} onChange={(event) => setCategoryFilter(event.target.value)} placeholder="Music" /></label>
                    <label>Location<input value={locationFilter} onChange={(event) => setLocationFilter(event.target.value)} placeholder="City, venue, country" /></label>
                    <label>From<input type="date" value={dateFrom} onChange={(event) => setDateFrom(event.target.value)} /></label>
                    <label>To<input type="date" value={dateTo} onChange={(event) => setDateTo(event.target.value)} /></label>
                    <label>Max price<input type="number" min="0" step="0.01" value={maxPrice} onChange={(event) => setMaxPrice(event.target.value)} placeholder="50" /></label>
                    <button className="text-button" type="button" onClick={() => void loadEvents(1)}>Apply filters</button>
                </div>
            </section>

            <section className="events-section">
                <div className="section-heading">
                    <div><p className="eyebrow">DISCOVER</p><h2>On the calendar</h2></div>
                    <span className="result-count">{totalEvents} events</span>
                </div>
                {loading && <p className="state">Loading events...</p>}
                {error && <p className="state error">{error}. Start the FastAPI server to load live data.</p>}
                {!loading && !error && events.length === 0 && <p className="state">No published events match your search.</p>}
                <div className="event-grid">
                    {events.map((item) => (
                        <article className="event-card" key={item.id}>
                            <div className="event-date">{new Date(item.start_at).toLocaleDateString("en-GB", { day: "2-digit", month: "short" })}</div>
                            <p className="event-type">{item.event_type} / {item.city}</p>
                            <h3>{item.title}</h3>
                            <p>{item.description}</p>
                            <footer>{item.venue}<button className="card-link" type="button" onClick={() => openEvent(item)}>View event →</button></footer>
                        </article>
                    ))}
                </div>
                {totalEvents > pageSize && <div className="pagination">
                    <button className="text-button" type="button" disabled={page <= 1} onClick={() => void loadEvents(page - 1)}>← Previous</button>
                    <span>Page {page} of {Math.max(1, Math.ceil(totalEvents / pageSize))}</span>
                    <button className="text-button" type="button" disabled={page * pageSize >= totalEvents} onClick={() => void loadEvents(page + 1)}>Next →</button>
                </div>}
            </section>

            {selectedEvent && <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && setSelectedEvent(null)}>
                <section className="auth-modal" role="dialog" aria-modal="true" aria-labelledby="event-title">
                    <button className="modal-close" type="button" aria-label="Close" onClick={() => setSelectedEvent(null)}>×</button>
                    <p className="eyebrow">{selectedEvent.event_type} / {selectedEvent.city}</p>
                    <h2 id="event-title">{selectedEvent.title}</h2>
                    <p className="hero-copy">{selectedEvent.description}</p>
                    <p>{selectedEvent.venue} · {new Date(selectedEvent.start_at).toLocaleString()}</p>
                    {selectedEvent.media.length > 0 && <div className="media-gallery">{selectedEvent.media.map((url) => <img key={url} src={url} alt={selectedEvent.title} loading="lazy" />)}</div>}
                    {selectedEvent.latitude && selectedEvent.longitude && (
                        <iframe
                            className="event-map"
                            title="Event location"
                            loading="lazy"
                            src={`https://www.openstreetmap.org/export/embed.html?bbox=${Number(selectedEvent.longitude) - 0.01}%2C${Number(selectedEvent.latitude) - 0.01}%2C${Number(selectedEvent.longitude) + 0.01}%2C${Number(selectedEvent.latitude) + 0.01}&layer=mapnik&marker=${selectedEvent.latitude}%2C${selectedEvent.longitude}`}
                        />
                    )}
                    {user?.role === "participant" ? (bookingConfirmStep ? (() => {
                        const ticketDetails = selectedEvent.ticket_types.find((ticket) => ticket.id === selectedTicket);
                        const totalCost = ticketDetails ? (Number(ticketDetails.price) * ticketQuantity).toFixed(2) : "0.00";
                        return (
                            <form className="auth-form" onSubmit={submitBooking}>
                                <p className="confirm-summary">Confirm {ticketQuantity} × {ticketDetails?.name} for <strong>€{totalCost}</strong>. This booking cannot be undone once submitted.</p>
                                <button className="primary-button auth-submit" type="submit">Yes, confirm booking</button>
                                <button className="text-button" type="button" onClick={() => setBookingConfirmStep(false)}>Back</button>
                                {bookingMessage && <p className="auth-message">{bookingMessage}</p>}
                                {bookingError && <p className="state error">{bookingError}</p>}
                            </form>
                        );
                    })() : <form className="auth-form" onSubmit={submitBooking}>
                        <label>Ticket type<select value={selectedTicket} onChange={(event) => setSelectedTicket(event.target.value)} required>{selectedEvent.ticket_types.map((ticket) => <option key={ticket.id} value={ticket.id} disabled={ticket.available === 0}>{ticket.name} · €{ticket.price} · {ticket.available} available</option>)}</select></label>
                        <label>Number of tickets<input type="number" min="1" max="10" value={ticketQuantity} onChange={(event) => setTicketQuantity(Number(event.target.value))} required /></label>
                        <button className="primary-button auth-submit" type="submit">Review booking</button>
                        {bookingMessage && <p className="auth-message">{bookingMessage}</p>}
                        {bookingError && <p className="state error">{bookingError}</p>}
                    </form>) : <p className="state">Sign in as a participant to make a reservation.</p>}
                    {bookingMessage && <form className="auth-form contact-form" onSubmit={sendContactMessage}>
                        <label>Message the organizer<textarea value={contactBody} onChange={(event) => setContactBody(event.target.value)} required rows={3} /></label>
                        <button className="text-button" type="submit">Send message</button>
                        {contactMessage && <p className="auth-message">{contactMessage}</p>}
                    </form>}
                </section>
            </div>}

            {dashboardOpen && <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && setDashboardOpen(false)}>
                <section className="auth-modal dashboard-modal" role="dialog" aria-modal="true" aria-labelledby="dashboard-title">
                    <button className="modal-close" type="button" aria-label="Close" onClick={() => setDashboardOpen(false)}>×</button>
                    <p className="eyebrow">{user?.role === "admin" ? "ADMINISTRATION" : "YOUR EVENTS"}</p>
                    <h2 id="dashboard-title">Dashboard</h2>
                    {dashboardError && <p className="state error">{dashboardError}</p>}
                    {user?.role === "admin" && <div className="dashboard-list">
                        <div className="tab-row">
                            <button className={`tab-button${userStatusFilter === "pending" ? " active" : ""}`} type="button" onClick={() => loadUsers("pending")}>Pending</button>
                            <button className={`tab-button${userStatusFilter === "approved" ? " active" : ""}`} type="button" onClick={() => loadUsers("approved")}>Approved</button>
                            <button className={`tab-button${userStatusFilter === "rejected" ? " active" : ""}`} type="button" onClick={() => loadUsers("rejected")}>Rejected</button>
                            <button className={`tab-button${userStatusFilter === "all" ? " active" : ""}`} type="button" onClick={() => loadUsers("all")}>All</button>
                        </div>
                        {managedUsers.length === 0 ? <p className="state">No users in this list.</p> : managedUsers.map((managedUser) => <div className="dashboard-row" key={managedUser.id}><button className="row-link" type="button" onClick={() => openUserDetail(managedUser.id)}><strong>{managedUser.username}</strong><span>{managedUser.email} · {managedUser.role} · {managedUser.status}</span></button>{managedUser.status === "pending" && <div className="row-actions"><button className="small-button" type="button" onClick={() => reviewUser(managedUser.id, "approve")}>Approve</button><button className="small-button danger-button" type="button" onClick={() => reviewUser(managedUser.id, "reject")}>Reject</button></div>}</div>)}
                        <div className="tab-row">
                            <button className="text-button" type="button" onClick={() => downloadExport("xml")}>Export events (XML)</button>
                            <button className="text-button" type="button" onClick={() => downloadExport("json")}>Export events (JSON)</button>
                        </div>
                    </div>}
                    {user?.role === "organizer" && <div className="dashboard-list">
                        <button className="small-button" type="button" onClick={() => { setDashboardOpen(false); setCreateEventOpen(true); }}>+ New event</button>
                        {ownedEvents.length === 0 ? <p className="state">You have not created any events.</p> : ownedEvents.map((ownedEvent) => <div className="dashboard-row" key={ownedEvent.id}><div><strong>{ownedEvent.title}</strong><span>{ownedEvent.status} · {ownedEvent.city}</span></div><div className="row-actions"><button className="small-button" type="button" onClick={() => viewEventBookings(ownedEvent)}>Bookings</button>{ownedEvent.status === "draft" && <button className="small-button" type="button" onClick={() => updateOwnedEvent(ownedEvent.id, "publish")}>Publish</button>}{(ownedEvent.status === "draft" || ownedEvent.status === "published") && <button className="small-button" type="button" onClick={() => openEditEvent(ownedEvent)}>Edit</button>}{ownedEvent.status === "published" && <button className="small-button danger-button" type="button" onClick={() => updateOwnedEvent(ownedEvent.id, "cancel")}>Cancel</button>}{ownedEvent.status === "draft" && <button className="small-button danger-button" type="button" onClick={() => updateOwnedEvent(ownedEvent.id, "delete")}>Delete</button>}</div></div>)}
                    </div>}
                    {user?.role === "participant" && <div className="dashboard-list">{recommendations.length === 0 ? <p className="state">Explore a few events to get recommendations.</p> : recommendations.map((recommendation) => <div className="dashboard-row" key={recommendation.event_id}><div><strong>{recommendation.title}</strong><span>{recommendation.reason}</span></div><span className="score-label">{recommendation.score.toFixed(2)}</span></div>)}</div>}
                </section>
            </div>}

            {selectedUserDetail && <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && setSelectedUserDetail(null)}>
                <section className="auth-modal" role="dialog" aria-modal="true" aria-labelledby="user-detail-title">
                    <button className="modal-close" type="button" aria-label="Close" onClick={() => setSelectedUserDetail(null)}>×</button>
                    <p className="eyebrow">USER DETAILS</p>
                    <h2 id="user-detail-title">{selectedUserDetail.username}</h2>
                    <div className="detail-grid">
                        <div><span>Name</span><strong>{selectedUserDetail.first_name} {selectedUserDetail.last_name}</strong></div>
                        <div><span>Email</span><strong>{selectedUserDetail.email}</strong></div>
                        <div><span>Phone</span><strong>{selectedUserDetail.phone}</strong></div>
                        <div><span>Address</span><strong>{selectedUserDetail.address}</strong></div>
                        <div><span>City</span><strong>{selectedUserDetail.city}</strong></div>
                        <div><span>Country</span><strong>{selectedUserDetail.country}</strong></div>
                        <div><span>Tax ID</span><strong>{selectedUserDetail.tax_id}</strong></div>
                        <div><span>Role</span><strong>{selectedUserDetail.role}</strong></div>
                        <div><span>Status</span><strong>{selectedUserDetail.status}</strong></div>
                        <div><span>Registered</span><strong>{new Date(selectedUserDetail.created_at).toLocaleString()}</strong></div>
                    </div>
                    {selectedUserDetail.status === "pending" && <div className="row-actions detail-actions">
                        <button className="small-button" type="button" onClick={() => reviewUser(selectedUserDetail.id, "approve")}>Approve</button>
                        <button className="small-button danger-button" type="button" onClick={() => reviewUser(selectedUserDetail.id, "reject")}>Reject</button>
                    </div>}
                </section>
            </div>}

            {viewingBookingsEvent && <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && setViewingBookingsEvent(null)}>
                <section className="auth-modal dashboard-modal" role="dialog" aria-modal="true" aria-labelledby="bookings-title">
                    <button className="modal-close" type="button" aria-label="Close" onClick={() => setViewingBookingsEvent(null)}>×</button>
                    <p className="eyebrow">BOOKINGS</p>
                    <h2 id="bookings-title">{viewingBookingsEvent.title}</h2>
                    {eventBookingsError && <p className="state error">{eventBookingsError}</p>}
                    <div className="dashboard-list">
                        {eventBookings.length === 0 ? <p className="state">No bookings yet for this event.</p> : eventBookings.map((booking) => (
                            <div className="dashboard-row" key={booking.id}>
                                <div>
                                    <strong>{booking.attendee_username}</strong>
                                    <span>{booking.ticket_type_name} · {booking.number_of_tickets} ticket(s) · €{booking.total_cost} · {booking.status}</span>
                                </div>
                                <span className="score-label">{new Date(booking.created_at).toLocaleDateString()}</span>
                            </div>
                        ))}
                    </div>
                </section>
            </div>}

            {messagesOpen && <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && setMessagesOpen(false)}>
                <section className="auth-modal dashboard-modal" role="dialog" aria-modal="true" aria-labelledby="messages-title">
                    <button className="modal-close" type="button" aria-label="Close" onClick={() => setMessagesOpen(false)}>×</button>
                    <p className="eyebrow">CONVERSATIONS</p>
                    <h2 id="messages-title">Messages</h2>
                    <div className="tab-row">
                        <button className={`tab-button${messagesTab === "inbox" ? " active" : ""}`} type="button" onClick={() => openMessages("inbox")}>Inbox</button>
                        <button className={`tab-button${messagesTab === "sent" ? " active" : ""}`} type="button" onClick={() => openMessages("sent")}>Sent</button>
                    </div>
                    {messagesError && <p className="state error">{messagesError}</p>}
                    <div className="dashboard-list">
                        {(messagesTab === "inbox" ? inboxMessages : sentMessages).length === 0 ? <p className="state">No messages here.</p> : (messagesTab === "inbox" ? inboxMessages : sentMessages).map((message) => (
                            <div className="dashboard-row" key={message.id}>
                                <div>
                                    <strong>{message.event_title}</strong>
                                    <span>{messagesTab === "inbox" ? `From ${message.sender_username}` : `To ${message.recipient_username}`} · {new Date(message.created_at).toLocaleString()}</span>
                                    <p className="message-body">{message.body}</p>
                                </div>
                                <button className="small-button danger-button" type="button" onClick={() => deleteMessage(message.id, messagesTab)}>Delete</button>
                            </div>
                        ))}
                    </div>
                </section>
            </div>}

            {createEventOpen && <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && setCreateEventOpen(false)}>
                <section className="auth-modal dashboard-modal" role="dialog" aria-modal="true" aria-labelledby="create-event-title">
                    <button className="modal-close" type="button" aria-label="Close" onClick={() => setCreateEventOpen(false)}>×</button>
                    <p className="eyebrow">NEW EVENT</p>
                    <h2 id="create-event-title">Create an event</h2>
                    <form className="auth-form" onSubmit={submitCreateEvent}>
                        <label>Title<input name="title" required /></label>
                        <label>Categories (comma separated)<input name="categories" placeholder="Music, Live Performance" required /></label>
                        <div className="form-row"><label>Event type<input name="event_type" required /></label><label>Venue<input name="venue" required /></label></div>
                        <label>Address<input name="address" required /></label>
                        <div className="form-row"><label>City<input name="city" required /></label><label>Country<input name="country" defaultValue="Greece" required /></label></div>
                        <div className="form-row"><label>Latitude (optional)<input name="latitude" type="number" step="0.000001" min="-90" max="90" /></label><label>Longitude (optional)<input name="longitude" type="number" step="0.000001" min="-180" max="180" /></label></div>
                        <div className="form-row"><label>Start<input name="start_at" type="datetime-local" required /></label><label>End<input name="end_at" type="datetime-local" required /></label></div>
                        <label>Capacity<input name="capacity" type="number" min="1" required /></label>
                        <label>Description<textarea name="description" rows={3} required /></label>
                        <label>Photo URLs (one per line, optional)<textarea value={mediaUrlsText} onChange={(event) => setMediaUrlsText(event.target.value)} rows={2} placeholder="https://example.com/cover.jpg" /></label>
                        <div className="ticket-editor">
                            <p className="eyebrow">TICKET TYPES</p>
                            {ticketRows.map((row, index) => (
                                <div className="form-row ticket-row" key={index}>
                                    <label>Name<input value={row.name} onChange={(event) => updateTicketRow(index, "name", event.target.value)} required /></label>
                                    <label>Price<input type="number" min="0" step="0.01" value={row.price} onChange={(event) => updateTicketRow(index, "price", event.target.value)} required /></label>
                                    <label>Quantity<input type="number" min="1" value={row.quantity} onChange={(event) => updateTicketRow(index, "quantity", event.target.value)} required /></label>
                                </div>
                            ))}
                            <button className="text-button" type="button" onClick={() => setTicketRows((current) => [...current, { name: "", price: "", quantity: "" }])}>+ Add ticket type</button>
                        </div>
                        <button className="primary-button auth-submit" type="submit">Create draft event</button>
                        {createEventMessage && <p className="auth-message">{createEventMessage}</p>}
                        {createEventError && <p className="state error">{createEventError}</p>}
                    </form>
                </section>
            </div>}

            {editingEvent && <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && setEditingEvent(null)}>
                <section className="auth-modal dashboard-modal" role="dialog" aria-modal="true" aria-labelledby="edit-event-title">
                    <button className="modal-close" type="button" aria-label="Close" onClick={() => setEditingEvent(null)}>×</button>
                    <p className="eyebrow">EDIT EVENT</p>
                    <h2 id="edit-event-title">{editingEvent.title}</h2>
                    <form className="auth-form" onSubmit={submitEditEvent}>
                        <label>Title<input name="title" defaultValue={editingEvent.title} required /></label>
                        <div className="form-row"><label>Event type<input name="event_type" defaultValue={editingEvent.event_type} required /></label><label>Venue<input name="venue" defaultValue={editingEvent.venue} required /></label></div>
                        <label>Address<input name="address" defaultValue={editingEvent.address} required /></label>
                        <div className="form-row"><label>City<input name="city" defaultValue={editingEvent.city} required /></label><label>Country<input name="country" defaultValue={editingEvent.country} required /></label></div>
                        <div className="form-row"><label>Latitude (optional)<input name="latitude" type="number" step="0.000001" min="-90" max="90" defaultValue={editingEvent.latitude ?? ""} /></label><label>Longitude (optional)<input name="longitude" type="number" step="0.000001" min="-180" max="180" defaultValue={editingEvent.longitude ?? ""} /></label></div>
                        <div className="form-row"><label>Start<input name="start_at" type="datetime-local" defaultValue={toDateTimeLocal(editingEvent.start_at)} required /></label><label>End<input name="end_at" type="datetime-local" defaultValue={toDateTimeLocal(editingEvent.end_at)} required /></label></div>
                        <label>Description<textarea name="description" defaultValue={editingEvent.description} rows={3} required /></label>
                        <label>Photo URLs (one per line, optional)<textarea value={mediaUrlsText} onChange={(event) => setMediaUrlsText(event.target.value)} rows={2} /></label>
                        <button className="primary-button auth-submit" type="submit">Save changes</button>
                        {editEventMessage && <p className="auth-message">{editEventMessage}</p>}
                        {editEventError && <p className="state error">{editEventError}</p>}
                    </form>
                </section>
            </div>}

            {authMode && <div className="modal-backdrop" role="presentation" onMouseDown={(event) => event.target === event.currentTarget && setAuthMode(null)}>
                <section className="auth-modal" role="dialog" aria-modal="true" aria-labelledby="auth-title">
                    <button className="modal-close" type="button" aria-label="Close" onClick={() => setAuthMode(null)}>×</button>
                    <p className="eyebrow">{authMode === "login" ? "WELCOME BACK" : "JOIN GATHER"}</p>
                    <h2 id="auth-title">{authMode === "login" ? "Sign in" : "Create your account"}</h2>
                    <form className="auth-form" onSubmit={submitAuth}>
                        <label>Username<input name="username" required minLength={3} /></label>
                        {authMode === "register" && <><div className="form-row"><label>First name<input name="first_name" required /></label><label>Last name<input name="last_name" required /></label></div><label>Email<input name="email" type="email" required /></label><div className="form-row"><label>Phone<input name="phone" required /></label><label>Tax ID<input name="tax_id" required /></label></div><label>Address<input name="address" required /></label><div className="form-row"><label>City<input name="city" required /></label><label>Country<input name="country" defaultValue="Greece" required /></label></div><label>Requested role<select name="requested_role" defaultValue="participant"><option value="participant">Participant</option><option value="organizer">Organizer</option></select></label></>}
                        <label>Password<input name="password" type="password" minLength={8} required /></label>
                        {authMode === "register" && <label>Confirm password<input name="password_confirmation" type="password" minLength={8} required /></label>}
                        <button className="primary-button auth-submit" type="submit">{authMode === "login" ? "Sign in" : "Submit registration"}</button>
                    </form>
                    {authMessage && <p className="auth-message">{authMessage}</p>}
                    {authError && <p className="state error">{authError}</p>}
                    <button className="switch-auth" type="button" onClick={() => { setAuthMode(authMode === "login" ? "register" : "login"); setAuthError(""); setAuthMessage(""); }}>{authMode === "login" ? "Need an account? Register" : "Already registered? Sign in"}</button>
                </section>
            </div>}
        </main>
    );
}