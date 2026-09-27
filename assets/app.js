(() => {
  "use strict";

  const DB_KEY = "may_sheep_market_pages_v1";
  const SESSION_KEY = "may_sheep_market_session_v1";
  const FLASH_KEY = "may_sheep_market_flash_v1";
  const app = document.querySelector("#app");
  const money = (value) => Number(value).toFixed(2);
  const now = () => new Date().toISOString();
  const uid = (prefix) => `${prefix}_${Date.now()}_${Math.random().toString(36).slice(2, 8)}`;
  const esc = (value = "") => String(value).replace(/[&<>'"]/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;",'"':"&quot;"})[char]);

  function avatarSvg(label, colors = ["#e8e8ed", "#8e8e93"]) {
    const initial = esc(String(label || "羊").slice(0, 1).toUpperCase());
    return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(`<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 120"><defs><linearGradient id="g" x2="1" y2="1"><stop stop-color="${colors[0]}"/><stop offset="1" stop-color="${colors[1]}"/></linearGradient></defs><circle cx="60" cy="60" r="60" fill="url(#g)"/><circle cx="60" cy="50" r="27" fill="white" opacity=".9"/><text x="60" y="59" text-anchor="middle" font-family="Arial" font-size="27" font-weight="700" fill="#1d1d1f">${initial}</text><path d="M25 112c4-24 18-36 35-36s31 12 35 36" fill="white" opacity=".9"/></svg>`)}`;
  }

  function seedDb() {
    const users = [
      {id:"u_mewo",username:"MEWO",password:"123456",email:"mewo@example.com",gender:"F",birthDate:"2003-07-14",avatar:avatarSvg("M",["#4b5563","#111827"]),address:{state:"中国",city:"青岛",street:"崂山区松岭路238号"},wallet:999999,payPassword:"999999",shop:{name:"MEWO的小店",avatar:avatarSvg("M",["#dbeafe","#60a5fa"])}},
      {id:"u_cat",username:"cat",password:"123456",email:"cat@example.com",gender:"N",birthDate:"",avatar:avatarSvg("C",["#f3f4f6","#9ca3af"]),address:{state:"中国",city:"青岛",street:"市南区演示路1号"},wallet:999999,payPassword:"999999",shop:{name:"cat的店铺",avatar:avatarSvg("店",["#fef3c7","#f59e0b"])}}
    ];
    return {
      version:1,
      users,
      products:[
        {id:"p_air",ownerId:"u_cat",title:"空调",description:"哈机密：咪的天！空调吹得咪脑袋疼 😾",price:39999,inventory:500,sale:0,category:"电器",emoji:"❄️",image:"",updatedAt:now()},
        {id:"p_noodle",ownerId:"u_cat",title:"螺蛳粉",description:"哈机密：我认证过了，真的很香！姨姨们放心下单！",price:23,inventory:33,sale:0,category:"食品",emoji:"🍜",image:"",updatedAt:now()},
        {id:"p_coffee",ownerId:"u_cat",title:"猫屎咖啡",description:"哈机密：姨姨们，咖啡里面的屎都是我拉的哦，大家不要怀疑啦！",price:45.5,inventory:9999,sale:0,category:"食品",emoji:"☕",image:"",updatedAt:now()}
      ],
      carts:{u_mewo:[],u_cat:[]},
      orders:[],
      comments:[
        {id:"c1",productId:"p_noodle",userId:"u_mewo",content:"螺蛳粉一般，但小猫绝了 😻",replyTo:null,createdAt:"2026-07-14T12:23:00.000Z"},
        {id:"c2",productId:"p_noodle",userId:"u_cat",content:"咪的天，小猫你吃点好的吧！这个螺蛳粉真一般！",replyTo:"c1",createdAt:"2026-07-14T12:23:30.000Z"}
      ]
    };
  }

  function loadDb() {
    try {
      const parsed = JSON.parse(localStorage.getItem(DB_KEY));
      if (parsed && parsed.version === 1) return parsed;
    } catch (_) {}
    const db = seedDb();
    saveDb(db);
    return db;
  }
  function saveDb(db) { localStorage.setItem(DB_KEY, JSON.stringify(db)); }
  function sessionId() { return sessionStorage.getItem(SESSION_KEY) || ""; }
  function currentUser(db) { return db.users.find((item) => item.id === sessionId()) || null; }
  function setSession(id) { id ? sessionStorage.setItem(SESSION_KEY, id) : sessionStorage.removeItem(SESSION_KEY); }
  function setFlash(text, type = "success") { sessionStorage.setItem(FLASH_KEY, JSON.stringify({text,type})); }
  function takeFlash() {
    try { const data = JSON.parse(sessionStorage.getItem(FLASH_KEY)); sessionStorage.removeItem(FLASH_KEY); return data; }
    catch (_) { return null; }
  }
  function findUser(db, id) { return db.users.find((item) => item.id === id); }
  function findProduct(db, id) { return db.products.find((item) => item.id === id); }
  function route() {
    const raw = location.hash.replace(/^#\/?/, "") || (sessionId() ? "home" : "login");
    const [name, query = ""] = raw.split("?");
    return {name, params:new URLSearchParams(query)};
  }
  function go(target) { location.hash = `#/${target}`; }
  function imageMarkup(product, className = "product-art") {
    return `<div class="${className}">${product.image ? `<img src="${product.image}" alt="${esc(product.title)}">` : `<span aria-hidden="true">${esc(product.emoji || "🛍️")}</span>`}</div>`;
  }
  function completeAddress(user) { return user.address && [user.address.state,user.address.city,user.address.street].every((value) => value && value !== "未设置"); }
  function roleFor(db, userId, product) { return product.ownerId === userId ? "卖家评论" : "买家评论"; }
  function messageHtml(message) { return message ? `<div class="messages"><div class="message ${esc(message.type)}">${esc(message.text)}</div></div>` : ""; }

  function header(db, user, query = "") {
    if (!user) return "";
    return `<header class="topbar">
      <a class="brand" href="#/home"><span class="brand-mark">羊</span><span>每羊小超市</span></a>
      <form class="top-search" data-action="search"><label class="visually-hidden" for="top-query">搜索</label><input id="top-query" name="query" value="${esc(query)}" placeholder="搜索商品、分类或店铺"><button>搜索</button></form>
      <nav class="nav-links"><a href="#/store">我的商店</a><a href="#/cart">购物车</a><a href="#/orders">订单</a><a class="avatar-link" href="#/profile"><img src="${user.avatar}" alt="${esc(user.username)}"><span>${esc(user.username)}</span></a></nav>
    </header>`;
  }
  function layout(db, user, content, query = "") {
    return `${header(db,user,query)}<main class="${user ? "page" : "auth-page"}">${messageHtml(takeFlash())}${content}</main>${user ? '<div class="data-note">演示数据仅保存在当前浏览器</div>' : ""}`;
  }
  function requireUser(db) {
    const user = currentUser(db);
    if (!user) { setFlash("请先登录后继续操作。", "warning"); go("login"); return null; }
    return user;
  }

  function productCard(db, product) {
    const owner = findUser(db, product.ownerId);
    return `<a class="product-card" href="#/product?id=${encodeURIComponent(product.id)}">${imageMarkup(product)}<div class="body"><h3>${esc(product.title)}</h3><p class="muted">${esc(product.description)}</p><div class="product-meta"><span>${esc(product.category)}</span><span>库存 ${product.inventory}</span></div><div class="product-meta"><strong class="price">￥${money(product.price)}</strong><span>销量 ${product.sale}</span></div><span class="muted">${esc(owner?.shop?.name || "未知店铺")}</span></div></a>`;
  }

  function renderLogin(db) {
    const content = `<section class="auth-card"><p class="eyebrow">Welcome Back</p><h1>登录每羊小超市</h1><p class="muted">登录后即可浏览商品、管理购物车和体验卖家流程。</p>
      <form class="form-stack" data-action="login"><div class="field"><label for="username">用户名</label><input id="username" name="username" autocomplete="username" required></div><div class="field"><label for="password">密码</label><input id="password" type="password" name="password" autocomplete="current-password" required></div><button>登录</button></form>
      <div class="actions" style="margin-top:16px"><a href="#/register">注册账号</a><a href="#/recover">找回账号</a></div>
      <div class="demo-box"><strong>本地演示账号</strong><p style="margin:8px 0 4px">买家：<code>MEWO</code> / <code>123456</code></p><p style="margin:0 0 10px">卖家：<code>cat</code> / <code>123456</code></p><button class="small" data-click="demo-login" data-user="MEWO">一键进入买家账号</button></div>
    </section>`;
    app.innerHTML = layout(db,null,content);
  }

  function renderRegister(db) {
    const code = sessionStorage.getItem("may_sheep_register_code") || "";
    const content = `<section class="auth-card"><p class="eyebrow">Create Account</p><h1>创建你的市场账号</h1><p class="muted">静态演示不会发送邮件，验证码会直接显示在当前页面。</p>
      ${code ? `<div class="message success">本次验证码：<strong>${esc(code)}</strong></div>` : ""}
      <form class="form-stack" data-action="register"><div class="field"><label>用户名</label><input name="username" maxlength="18" required></div><div class="field"><label>密码</label><input type="password" name="password" minlength="6" required></div><div class="field"><label>邮箱</label><input type="email" name="email" required></div><div class="field"><label>验证码</label><div class="actions"><input name="code" maxlength="6" placeholder="6 位验证码"><button class="secondary" type="button" data-click="send-code">生成验证码</button></div></div><button>注册</button></form><p class="muted" style="margin-top:16px">已有账号？<a href="#/login">立即登录</a></p></section>`;
    app.innerHTML = layout(db,null,content);
  }

  function renderRecover(db) {
    const code = sessionStorage.getItem("may_sheep_recover_code") || "";
    const content = `<section class="auth-card"><p class="eyebrow">Account Recovery</p><h1>重设用户名和密码</h1><p class="muted">输入已注册邮箱，通过本地验证码更新账号信息。</p>${code ? `<div class="message success">本次验证码：<strong>${esc(code)}</strong></div>` : ""}<form class="form-stack" data-action="recover"><div class="field"><label>新用户名</label><input name="username" maxlength="18" required></div><div class="field"><label>新密码</label><input type="password" name="password" minlength="6" required></div><div class="field"><label>注册邮箱</label><input type="email" name="email" required></div><div class="field"><label>验证码</label><div class="actions"><input name="code" maxlength="6"><button class="secondary" type="button" data-click="send-recover-code">生成验证码</button></div></div><button>确认修改</button></form><p class="muted" style="margin-top:16px"><a href="#/login">返回登录</a></p></section>`;
    app.innerHTML = layout(db,null,content);
  }

  function renderHome(db, user, params) {
    const q = (params.get("q") || "").trim().toLowerCase();
    const products = db.products.filter((p) => p.inventory > 0 && (!q || [p.title,p.description,p.category,findUser(db,p.ownerId)?.shop?.name].join(" ").toLowerCase().includes(q))).sort((a,b) => b.sale-a.sale || b.updatedAt.localeCompare(a.updatedAt));
    const content = `<section class="hero-panel"><div><p class="eyebrow">精选市集</p><h1>把小店、好物和订单放进一个清爽的 Django 商城。</h1><p class="muted">浏览商品、加入购物车、立即购买，卖家也可以直接在自己的店铺里发布和管理商品。</p><div class="actions"><a class="btn" href="#/store">管理我的商店</a><a class="btn secondary" href="#/cart">查看购物车</a></div></div><div class="stat-strip"><div class="stat"><strong>${products.length}</strong><span class="muted">在售商品</span></div><div class="stat"><strong>6</strong><span class="muted">位默认支付密码</span></div><div class="stat"><strong>Local</strong><span class="muted">浏览器存储</span></div></div></section>
      <div class="section-head"><div><h2>${q ? "搜索结果" : "热门商品"}</h2><p class="muted">${q ? `关键词“${esc(q)}”，共 ${products.length} 件。` : "按销量和更新时间排序。"}</p></div>${q ? '<a class="btn secondary" href="#/home">清除搜索</a>' : ""}</div>
      ${products.length ? `<section class="product-grid">${products.map((p) => productCard(db,p)).join("")}</section>` : '<div class="empty-state">没有找到匹配的商品。</div>'}`;
    app.innerHTML = layout(db,user,content,q);
  }

  function renderProduct(db, user, params) {
    const product = findProduct(db, params.get("id"));
    if (!product) return renderNotFound(db,user);
    const owner = findUser(db,product.ownerId);
    const isOwner = product.ownerId === user.id;
    const comments = db.comments.filter((c) => c.productId === product.id && !c.replyTo).sort((a,b) => b.createdAt.localeCompare(a.createdAt));
    const commentHtml = comments.map((comment) => {
      const author = findUser(db,comment.userId);
      const replies = db.comments.filter((item) => item.replyTo === comment.id).map((reply) => {
        const replyAuthor = findUser(db,reply.userId);
        const canDelete = reply.userId === user.id || isOwner;
        return `<li class="comment-item"><div class="comment-meta"><strong>${esc(replyAuthor?.username || "已注销用户")}</strong><span>回复 ${esc(author?.username || "已注销用户")}</span><span>${new Date(reply.createdAt).toLocaleString("zh-CN")}</span></div><p style="margin:12px 0">${esc(reply.content)}</p>${canDelete ? `<button class="danger small" data-click="delete-comment" data-id="${reply.id}">删除</button>` : ""}</li>`;
      }).join("");
      const canDelete = comment.userId === user.id || isOwner;
      return `<li class="comment-item"><div class="comment-meta"><span class="comment-author"><img class="avatar" src="${author?.avatar || avatarSvg("?")}" alt="">${esc(author?.username || "已注销用户")}</span><span>${roleFor(db,comment.userId,product)}</span><span>${new Date(comment.createdAt).toLocaleString("zh-CN")}</span></div><p style="margin:12px 0">${esc(comment.content)}</p><div class="actions"><button class="secondary small" data-click="reply" data-id="${comment.id}">回复</button>${canDelete ? `<button class="danger small" data-click="delete-comment" data-id="${comment.id}">删除</button>` : ""}</div>${replies ? `<ul class="reply-list">${replies}</ul>` : ""}</li>`;
    }).join("");
    const replyTo = params.get("reply");
    const replyComment = db.comments.find((c) => c.id === replyTo);
    const content = `<section class="split"><div class="panel" style="padding:16px">${imageMarkup(product,"detail-art")}</div><div class="summary"><p class="eyebrow">${esc(product.category)}</p><h1>${esc(product.title)}</h1><p class="muted">${esc(product.description)}</p><div class="stat-strip" style="margin:20px 0"><div class="stat"><strong>￥${money(product.price)}</strong><span class="muted">价格</span></div><div class="stat"><strong>${product.inventory}</strong><span class="muted">库存</span></div><div class="stat"><strong>${product.sale}</strong><span class="muted">销量</span></div></div><div class="line-item" style="grid-template-columns:56px 1fr;box-shadow:none"><img class="avatar" style="width:56px;height:56px" src="${owner.shop.avatar}" alt=""><div><strong>${esc(owner.shop.name)}</strong><p class="muted" style="margin:4px 0 0">店铺卖家</p></div></div><div class="actions" style="margin-top:18px">${isOwner ? `<a class="btn" href="#/product-form?id=${product.id}">修改商品信息</a>` : `<button class="secondary" data-click="add-cart" data-id="${product.id}" ${product.inventory < 1 ? "disabled" : ""}>加入购物车</button><a class="btn" href="#/pay?id=${product.id}">立即购买</a>`}<a class="btn secondary" href="#/home">返回首页</a></div></div></section>
      <section class="panel" style="padding:24px;margin-top:24px"><div class="section-head" style="margin-top:0"><div><p class="eyebrow">Reviews</p><h2>用户评论</h2></div></div>${commentHtml ? `<ul class="comment-list">${commentHtml}</ul>` : '<div class="empty-state">暂时还没有评论。</div>'}<form class="form-stack" style="margin-top:20px" data-action="comment"><input type="hidden" name="productId" value="${product.id}"><input type="hidden" name="replyTo" value="${esc(replyTo || "")}">${replyComment ? `<div class="message">正在回复 <strong>${esc(findUser(db,replyComment.userId)?.username || "用户")}</strong>：${esc(replyComment.content)}</div>` : ""}<div class="field"><label>写下你的评论</label><textarea name="content" placeholder="分享商品体验或回复评论" required></textarea></div><button>提交评论</button></form></section>`;
    app.innerHTML = layout(db,user,content);
  }

  function renderCart(db,user) {
    const cart = db.carts[user.id] || [];
    const items = cart.map((line) => ({...line,product:findProduct(db,line.productId)})).filter((line) => line.product);
    const total = items.reduce((sum,item) => sum + item.product.price * item.quantity,0);
    const list = items.map(({product,quantity}) => `<article class="line-item">${imageMarkup(product,"line-thumb")}<div><h3><a href="#/product?id=${product.id}">${esc(product.title)}</a></h3><p class="muted">单价 ￥${money(product.price)}，库存 ${product.inventory}</p><p class="price">小计 ￥${money(product.price*quantity)}</p></div><div class="actions"><form class="actions" data-action="cart-quantity"><input type="hidden" name="id" value="${product.id}"><input style="width:90px" type="number" min="1" max="${product.inventory}" value="${quantity}" name="quantity"><button class="secondary">修改</button></form><button class="danger" data-click="remove-cart" data-id="${product.id}">删除</button></div></article>`).join("");
    const content = `<div class="section-head"><div><p class="eyebrow">Cart</p><h1>我的购物车</h1></div><a class="btn secondary" href="#/home">继续选购</a></div>${items.length ? `<section class="split"><div class="cart-list">${list}</div><aside class="summary"><h2>合计 ￥${money(total)}</h2><p class="muted">默认演示支付密码为 999999。本页面不会发起真实支付。</p><form class="form-stack" data-action="checkout"><div class="field"><label>支付密码</label><input type="password" name="password" maxlength="6" placeholder="请输入 6 位支付密码" required></div><button>结算</button><button class="secondary" type="button" data-click="clear-cart">清空购物车</button></form></aside></section>` : '<div class="empty-state">购物车是空的，去首页挑几件商品吧。</div>'}`;
    app.innerHTML = layout(db,user,content);
  }

  function renderPay(db,user,params) {
    const product = findProduct(db,params.get("id"));
    if (!product || product.ownerId === user.id) return renderNotFound(db,user);
    const owner = findUser(db,product.ownerId);
    const content = `<section class="auth-card" style="margin:40px auto"><p class="eyebrow">May Sheep Pay</p><h1>确认支付</h1><p class="muted">支付给 ${esc(owner.shop.name)}</p><div class="stat" style="margin:18px 0"><strong>￥${money(product.price)}</strong><span class="muted">本次支付金额</span></div><form class="form-stack" data-action="pay"><input type="hidden" name="id" value="${product.id}"><div class="field"><label>支付密码</label><input type="password" name="password" maxlength="6" placeholder="默认演示密码 999999" required></div><button>立即支付</button><a class="btn secondary" href="#/product?id=${product.id}">返回商品</a></form></section>`;
    app.innerHTML = layout(db,user,content);
  }

  function renderOrders(db,user) {
    const orders = db.orders.filter((o) => o.buyerId === user.id || o.sellerId === user.id).sort((a,b) => b.placedAt.localeCompare(a.placedAt));
    const list = orders.map((order) => {
      const product = findProduct(db,order.productId) || {title:"已下架商品",emoji:"📦",image:""};
      const buyer = findUser(db,order.buyerId);
      const seller = findUser(db,order.sellerId);
      const isSeller = order.sellerId === user.id;
      const statusText = {NOT:"未发货",ING:"送货中",DONE:"已送达"}[order.shippingStatus];
      return `<article class="order-item">${imageMarkup(product,"line-thumb")}<div><p class="eyebrow">${isSeller ? "卖家视角" : "买家视角"}</p><h3>${esc(product.title)}</h3><p class="muted">${isSeller ? `买家：${esc(buyer?.username || "未知")}` : `店铺：${esc(seller?.shop?.name || "未知")}`}</p><p>数量：${order.quantity}，总价：￥${money(order.totalPrice)}</p><p>支付：支付完成，配送：${statusText}</p><p class="muted">下单时间：${new Date(order.placedAt).toLocaleString("zh-CN")}</p></div><div class="actions">${isSeller ? `<button class="secondary small" data-click="order-status" data-id="${order.id}" data-status="NOT">未发货</button><button class="secondary small" data-click="order-status" data-id="${order.id}" data-status="ING">已发货</button><button class="small" data-click="order-status" data-id="${order.id}" data-status="DONE">已签收</button>` : order.shippingStatus === "NOT" ? `<button class="danger small" data-click="delete-order" data-id="${order.id}">删除订单</button>` : ""}</div></article>`;
    }).join("");
    const content = `<div class="section-head"><div><p class="eyebrow">Orders</p><h1>我的订单</h1><p class="muted">同一页面展示买家订单，以及由你的店铺收到的卖家订单。</p></div><a class="btn secondary" href="#/home">返回首页</a></div>${list ? `<section class="order-list">${list}</section>` : '<div class="empty-state">暂无订单。</div>'}`;
    app.innerHTML = layout(db,user,content);
  }

  function renderStore(db,user) {
    const products = db.products.filter((p) => p.ownerId === user.id);
    const content = `<section class="hero-panel"><div><p class="eyebrow">Store Studio</p><h1>${esc(user.shop.name)}</h1><p class="muted">维护店铺形象、上架商品，并在订单页处理发货状态。</p><div class="actions"><a class="btn" href="#/product-form">上传商品</a><a class="btn secondary" href="#/store-settings">店铺设置</a><a class="btn secondary" href="#/home">返回首页</a></div></div><div class="summary"><img class="store-avatar-large" src="${user.shop.avatar}" alt=""><h3 style="margin-top:16px">${esc(user.shop.name)}</h3><p class="muted">当前共有 ${products.length} 件商品。</p></div></section><div class="section-head"><h2>店铺商品</h2></div>${products.length ? `<section class="product-grid">${products.map((p) => productCard(db,p)).join("")}</section>` : '<div class="empty-state">还没有上架商品，先发布第一件吧。</div>'}`;
    app.innerHTML = layout(db,user,content);
  }

  function renderStoreSettings(db,user) {
    const content = `<div class="section-head"><div><p class="eyebrow">Store Settings</p><h1>店铺设置</h1><p class="muted">统一的店铺名称和头像会显示在商品详情与订单中。</p></div><a class="btn secondary" href="#/store">返回店铺</a></div><section class="panel" style="padding:24px"><form class="form-stack" data-action="store-settings"><div class="actions"><img class="store-avatar-large" src="${user.shop.avatar}" alt=""><div class="field" style="min-width:260px"><label>店铺头像</label><input type="file" name="avatar" accept="image/*"></div></div><div class="field"><label>店铺名字</label><input name="name" value="${esc(user.shop.name)}" required></div><button>保存设置</button></form></section>`;
    app.innerHTML = layout(db,user,content);
  }

  function renderProductForm(db,user,params) {
    const product = params.get("id") ? findProduct(db,params.get("id")) : null;
    if (product && product.ownerId !== user.id) return renderNotFound(db,user);
    const title = product ? "编辑商品信息" : "上传新商品";
    const content = `<div class="section-head"><div><p class="eyebrow">${product ? "Edit Product" : "New Product"}</p><h1>${title}</h1><p class="muted">清晰的标题、图片和库存会让商品更容易被买家理解。</p></div><a class="btn secondary" href="#/store">返回店铺</a></div><section class="panel" style="padding:24px"><form class="form-stack" data-action="product-form"><input type="hidden" name="id" value="${product?.id || ""}"><div class="form-grid"><div class="field"><label>商品名称</label><input name="title" value="${esc(product?.title || "")}" required></div><div class="field"><label>商品分类</label><input name="category" value="${esc(product?.category || "")}" required></div><div class="field"><label>商品价格（元）</label><input type="number" name="price" step="0.01" min="0" value="${product?.price ?? ""}" required></div><div class="field"><label>库存数量</label><input type="number" name="inventory" min="0" value="${product?.inventory ?? 1}" required></div></div><div class="field"><label>商品描述</label><textarea name="description" required>${esc(product?.description || "")}</textarea></div><div class="field"><label>商品主图（可选，小于 1 MB）</label><input type="file" name="image" accept="image/*"></div><button>${product ? "保存修改" : "发布商品"}</button></form></section>`;
    app.innerHTML = layout(db,user,content);
  }

  function renderProfile(db,user) {
    const content = `<div class="section-head"><div><p class="eyebrow">Profile</p><h1>个人中心</h1><p class="muted">头像、收货地址和基础信息都会用于下单与订单展示。</p></div><div class="actions"><a class="btn secondary" href="#/change-password">修改密码</a><button class="danger" data-click="logout">退出登录</button></div></div><section class="panel" style="padding:24px"><form class="form-stack" data-action="profile"><div class="actions"><img class="profile-avatar" src="${user.avatar}" alt=""><div class="field" style="min-width:240px"><label>上传新头像（小于 1 MB）</label><input type="file" name="avatar" accept="image/*"></div></div><div class="form-grid"><div class="field"><label>邮箱</label><input type="email" value="${esc(user.email)}" disabled></div><div class="field"><label>性别</label><select name="gender"><option value="M" ${user.gender === "M" ? "selected" : ""}>男</option><option value="F" ${user.gender === "F" ? "selected" : ""}>女</option><option value="N" ${user.gender === "N" ? "selected" : ""}>未知</option></select></div><div class="field"><label>出生日期</label><input type="date" name="birthDate" value="${esc(user.birthDate)}"></div></div><h2>收货地址</h2><div class="form-grid"><div class="field"><label>国家或地区</label><input name="state" value="${esc(user.address.state)}"></div><div class="field"><label>城市</label><input name="city" value="${esc(user.address.city)}"></div><div class="field"><label>街道</label><input name="street" value="${esc(user.address.street)}"></div></div><button>保存资料</button></form><div style="margin-top:28px;padding-top:24px;border-top:1px solid var(--line)"><p class="muted">需要清空当前浏览器中的注册账号、订单、评论和商品变更时，可恢复初始演示数据。</p><button class="danger small" data-click="reset-data">恢复初始演示数据</button></div></section>`;
    app.innerHTML = layout(db,user,content);
  }

  function renderChangePassword(db,user) {
    const content = `<section class="auth-card" style="margin:40px auto"><p class="eyebrow">Security</p><h1>修改密码</h1><form class="form-stack" data-action="change-password"><div class="field"><label>当前密码</label><input type="password" name="oldPassword" required></div><div class="field"><label>新密码</label><input type="password" name="newPassword" minlength="6" required></div><button>保存新密码</button><a class="btn secondary" href="#/profile">返回个人中心</a></form></section>`;
    app.innerHTML = layout(db,user,content);
  }

  function renderNotFound(db,user) {
    app.innerHTML = layout(db,user,'<div class="empty-state"><h1>页面不存在</h1><p>请求的内容不存在或你没有访问权限。</p><a class="btn" href="#/home">返回首页</a></div>');
  }

  async function readImage(file) {
    if (!file || !file.size) return "";
    if (file.size > 1024 * 1024) throw new Error("图片不能超过 1 MB，否则浏览器本地存储可能溢出。");
    return await new Promise((resolve,reject) => { const reader = new FileReader(); reader.onload = () => resolve(reader.result); reader.onerror = reject; reader.readAsDataURL(file); });
  }

  function createOrder(db,buyer,product,quantity) {
    const total = product.price * quantity;
    const seller = findUser(db,product.ownerId);
    buyer.wallet -= total;
    seller.wallet += total;
    product.inventory -= quantity;
    product.sale += quantity;
    product.updatedAt = now();
    db.orders.push({id:uid("o"),buyerId:buyer.id,sellerId:seller.id,productId:product.id,quantity,totalPrice:total,paymentStatus:"DONE",shippingStatus:"NOT",address:{...buyer.address},placedAt:now()});
  }

  document.addEventListener("submit", async (event) => {
    const form = event.target.closest("form[data-action]");
    if (!form) return;
    event.preventDefault();
    const db = loadDb();
    const data = new FormData(form);
    const action = form.dataset.action;
    const user = currentUser(db);
    try {
      if (action === "search") return go(`home?q=${encodeURIComponent(data.get("query") || "")}`);
      if (action === "login") {
        const match = db.users.find((item) => item.username.toLowerCase() === String(data.get("username")).trim().toLowerCase() && item.password === data.get("password"));
        if (!match) throw new Error("用户名或密码错误。");
        setSession(match.id); setFlash(`欢迎回来，${match.username}。`); return go("home");
      }
      if (action === "register") {
        const username = String(data.get("username")).trim(); const email = String(data.get("email")).trim().toLowerCase();
        if (data.get("code") !== sessionStorage.getItem("may_sheep_register_code")) throw new Error("验证码不正确，请重新生成。");
        if (db.users.some((item) => item.username.toLowerCase() === username.toLowerCase())) throw new Error("用户名已存在。");
        if (db.users.some((item) => item.email.toLowerCase() === email)) throw new Error("邮箱已注册。");
        const id = uid("u"); db.users.push({id,username,password:data.get("password"),email,gender:"N",birthDate:"",avatar:avatarSvg(username),address:{state:"未设置",city:"未设置",street:"未设置"},wallet:999999,payPassword:"999999",shop:{name:`${username}的小店`,avatar:avatarSvg("店")}}); db.carts[id]=[]; saveDb(db); sessionStorage.removeItem("may_sheep_register_code"); setSession(id); setFlash("注册成功，已为你创建个人店铺和演示钱包。"); return go("home");
      }
      if (action === "recover") {
        if (data.get("code") !== sessionStorage.getItem("may_sheep_recover_code")) throw new Error("验证码不正确，请重新生成。");
        const account = db.users.find((item) => item.email.toLowerCase() === String(data.get("email")).trim().toLowerCase()); if (!account) throw new Error("未找到该邮箱对应的账号。");
        const name = String(data.get("username")).trim(); if (db.users.some((item) => item.id !== account.id && item.username.toLowerCase() === name.toLowerCase())) throw new Error("新用户名已被占用。");
        account.username=name; account.password=data.get("password"); saveDb(db); sessionStorage.removeItem("may_sheep_recover_code"); setFlash("账号信息已更新，请重新登录。"); return go("login");
      }
      if (!user) return go("login");
      if (action === "comment") { const content=String(data.get("content")).trim(); if(!content) throw new Error("评论不能为空。"); db.comments.push({id:uid("c"),productId:data.get("productId"),userId:user.id,content,replyTo:data.get("replyTo")||null,createdAt:now()}); saveDb(db); setFlash("评论已发布。"); return go(`product?id=${data.get("productId")}`); }
      if (action === "cart-quantity") { const line=(db.carts[user.id]||[]).find((item)=>item.productId===data.get("id")); const product=findProduct(db,data.get("id")); if(!line||!product) throw new Error("购物车商品不存在。"); line.quantity=Math.max(1,Math.min(Number(data.get("quantity"))||1,product.inventory)); saveDb(db); setFlash("购物车数量已更新。"); return render(); }
      if (action === "checkout") { const cart=db.carts[user.id]||[]; if(!cart.length) throw new Error("购物车为空。"); if(!completeAddress(user)) throw new Error("请先到个人中心设置完整地址。"); if(data.get("password")!==user.payPassword) throw new Error("支付密码错误。"); const lines=cart.map((line)=>({...line,product:findProduct(db,line.productId)})); if(lines.some((line)=>!line.product||line.quantity>line.product.inventory)) throw new Error("部分商品库存不足，请调整购物车。"); const total=lines.reduce((sum,line)=>sum+line.product.price*line.quantity,0); if(user.wallet<total) throw new Error("余额不足。"); lines.forEach((line)=>createOrder(db,user,line.product,line.quantity)); db.carts[user.id]=[]; saveDb(db); setFlash("结算成功，订单已生成。"); return go("orders"); }
      if (action === "pay") { const product=findProduct(db,data.get("id")); if(!product||product.inventory<1) throw new Error("商品不存在或已售罄。"); if(product.ownerId===user.id) throw new Error("不能购买自己店铺的商品。"); if(!completeAddress(user)) throw new Error("请先到个人中心设置完整地址。"); if(data.get("password")!==user.payPassword) throw new Error("支付密码错误。"); if(user.wallet<product.price) throw new Error("余额不足。"); createOrder(db,user,product,1); saveDb(db); setFlash("购买成功，订单已生成。"); return go("orders"); }
      if (action === "store-settings") { const image=await readImage(data.get("avatar")); user.shop.name=String(data.get("name")).trim(); if(image) user.shop.avatar=image; saveDb(db); setFlash("店铺设置已保存。"); return go("store"); }
      if (action === "product-form") { const id=data.get("id"); let product=id?findProduct(db,id):null; if(product&&product.ownerId!==user.id) throw new Error("只能编辑自己店铺的商品。"); const image=await readImage(data.get("image")); const fields={title:String(data.get("title")).trim(),category:String(data.get("category")).trim(),price:Number(data.get("price")),inventory:Number(data.get("inventory")),description:String(data.get("description")).trim(),updatedAt:now()}; if(!Number.isFinite(fields.price)||fields.price<0||!Number.isInteger(fields.inventory)||fields.inventory<0) throw new Error("价格或库存格式不正确。"); if(product){Object.assign(product,fields);if(image)product.image=image;}else{product={id:uid("p"),ownerId:user.id,...fields,sale:0,emoji:"🛍️",image};db.products.push(product);} saveDb(db); setFlash(id?"商品信息已更新。":"商品已发布。"); return go(`product?id=${product.id}`); }
      if (action === "profile") { const image=await readImage(data.get("avatar")); if(image)user.avatar=image; user.gender=data.get("gender"); user.birthDate=data.get("birthDate"); user.address={state:String(data.get("state")).trim()||"未设置",city:String(data.get("city")).trim()||"未设置",street:String(data.get("street")).trim()||"未设置"}; saveDb(db); setFlash("个人资料已保存。"); return render(); }
      if (action === "change-password") { if(data.get("oldPassword")!==user.password) throw new Error("当前密码错误。"); user.password=data.get("newPassword"); saveDb(db); setFlash("密码已修改。"); return go("profile"); }
    } catch (error) { setFlash(error.message || "操作未完成。","error"); render(); }
  });

  document.addEventListener("click", (event) => {
    const trigger = event.target.closest("[data-click]"); if(!trigger)return;
    const db=loadDb(); const user=currentUser(db); const action=trigger.dataset.click;
    try {
      if(action==="send-code"){sessionStorage.setItem("may_sheep_register_code",String(Math.floor(100000+Math.random()*900000)));return render();}
      if(action==="send-recover-code"){sessionStorage.setItem("may_sheep_recover_code",String(Math.floor(100000+Math.random()*900000)));return render();}
      if(action==="demo-login"){const demo=db.users.find((item)=>item.username===trigger.dataset.user);setSession(demo.id);setFlash("已进入本地演示账号。");return go("home");}
      if(!user)return go("login");
      if(action==="logout"){setSession("");setFlash("已退出登录。");return go("login");}
      if(action==="add-cart"){const product=findProduct(db,trigger.dataset.id);if(!product||product.inventory<1)throw new Error("商品已售罄。");if(product.ownerId===user.id)throw new Error("不能把自己店铺的商品加入购物车。");const cart=db.carts[user.id]||(db.carts[user.id]=[]);const line=cart.find((item)=>item.productId===product.id);if(line){if(line.quantity>=product.inventory)throw new Error("购物车数量已达到当前库存。");line.quantity+=1;}else cart.push({productId:product.id,quantity:1});saveDb(db);setFlash("已加入购物车。");return render();}
      if(action==="remove-cart"){db.carts[user.id]=(db.carts[user.id]||[]).filter((item)=>item.productId!==trigger.dataset.id);saveDb(db);setFlash("商品已移出购物车。");return render();}
      if(action==="clear-cart"){db.carts[user.id]=[];saveDb(db);setFlash("购物车已清空。");return render();}
      if(action==="reply"){const productId=route().params.get("id");return go(`product?id=${productId}&reply=${trigger.dataset.id}`);}
      if(action==="delete-comment"){const comment=db.comments.find((item)=>item.id===trigger.dataset.id);const product=findProduct(db,comment?.productId);if(!comment||!(comment.userId===user.id||product?.ownerId===user.id))throw new Error("无权删除这条评论。");const ids=new Set([comment.id,...db.comments.filter((item)=>item.replyTo===comment.id).map((item)=>item.id)]);db.comments=db.comments.filter((item)=>!ids.has(item.id));saveDb(db);setFlash("评论已删除。");return render();}
      if(action==="order-status"){const order=db.orders.find((item)=>item.id===trigger.dataset.id);if(!order||order.sellerId!==user.id)throw new Error("只能处理自己店铺的订单。");order.shippingStatus=trigger.dataset.status;saveDb(db);setFlash("订单状态已更新。");return render();}
      if(action==="delete-order"){const order=db.orders.find((item)=>item.id===trigger.dataset.id);if(!order||order.buyerId!==user.id||order.shippingStatus!=="NOT")throw new Error("订单已进入配送流程，不能删除。");db.orders=db.orders.filter((item)=>item.id!==order.id);saveDb(db);setFlash("订单已删除（演示版不执行退款）。","warning");return render();}
      if(action==="reset-data"){if(!confirm("确定恢复初始演示数据吗？当前浏览器中的注册账号、商品、订单和评论都会被清空。"))return;localStorage.removeItem(DB_KEY);setSession("");setFlash("已恢复初始演示数据，请重新登录。");return go("login");}
    } catch(error){setFlash(error.message||"操作未完成。","error");render();}
  });

  function render() {
    const db=loadDb(); const current=route();
    if(["login","register","recover"].includes(current.name)){ if(current.name==="login")return renderLogin(db); if(current.name==="register")return renderRegister(db); return renderRecover(db); }
    const user=requireUser(db); if(!user)return;
    const routes={home:renderHome,product:renderProduct,cart:renderCart,pay:renderPay,orders:renderOrders,store:renderStore,"store-settings":renderStoreSettings,"product-form":renderProductForm,profile:renderProfile,"change-password":renderChangePassword};
    const handler=routes[current.name]; if(!handler)return renderNotFound(db,user); handler(db,user,current.params);
  }

  window.addEventListener("hashchange", render);
  window.addEventListener("storage", render);
  render();
})();
