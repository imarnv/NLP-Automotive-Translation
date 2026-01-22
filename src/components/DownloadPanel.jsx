import React from 'react';

const DownloadPanel = ({ onReset, downloadUrl }) => {
    const formats = [
        { type: 'PDF', icon: '📄', label: 'Portable Document', url: downloadUrl },
        { type: 'DOC', icon: '📝', label: 'Word Document', url: '#' }, // Placeholder
        { type: 'XML', icon: '⚙️', label: 'XML Data', url: '#' }, // Placeholder
    ];

    return (
        <div className="w-full max-w-2xl mx-auto animate-fade-in-up">
            <div className="bg-white border border-gray-100 rounded-2xl shadow-xl overflow-hidden">
                <div className="bg-ggs-black text-white p-6 text-left">
                    <div className="flex items-center justify-between">
                        <div>
                            <h3 className="text-xl font-bold">Translation Complete</h3>
                            <p className="text-gray-400 text-sm mt-1">Your documents are ready for download.</p>
                        </div>
                        <div className="bg-green-500 rounded-full p-2">
                            <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M5 13l4 4L19 7" />
                            </svg>
                        </div>
                    </div>
                </div>

                <div className="p-6">
                    <div className="grid gap-4">
                        {formats.map((fmt) => (
                            <a
                                key={fmt.type}
                                href={fmt.url}
                                target="_blank"
                                rel="noreferrer"
                                className={`flex items-center justify-between p-4 rounded-xl border border-gray-100 hover:border-gray-300 hover:bg-gray-50 transition-all duration-200 group ${!fmt.url || fmt.url === '#' ? 'opacity-50 cursor-not-allowed' : ''}`}
                                onClick={(e) => (!fmt.url || fmt.url === '#') && e.preventDefault()}
                            >
                                <div className="flex items-center gap-4">
                                    <div className="w-12 h-12 bg-gray-100 rounded-lg flex items-center justify-center text-2xl group-hover:scale-110 transition-transform">
                                        {fmt.icon}
                                    </div>
                                    <div className="text-left">
                                        <p className="font-bold text-ggs-black">Download as {fmt.type}</p>
                                        <p className="text-xs text-gray-500">{fmt.label}</p>
                                    </div>
                                </div>
                                <div className="text-ggs-black opacity-0 group-hover:opacity-100 transition-opacity -translate-x-2 group-hover:translate-x-0 transform duration-200">
                                    <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                                    </svg>
                                </div>
                            </a>
                        ))}
                    </div>

                    <div className="mt-8 text-center">
                        <button
                            onClick={onReset}
                            className="text-sm text-gray-400 hover:text-ggs-black underline transition-colors"
                        >
                            Translate more documents
                        </button>
                    </div>
                </div>
            </div>

            <style>{`
                @keyframes fadeInUp {
                    from { opacity: 0; transform: translateY(20px); }
                    to { opacity: 1; transform: translateY(0); }
                }
                .animate-fade-in-up {
                    animation: fadeInUp 0.5s ease-out forwards;
                }
            `}</style>
        </div>
    );
};

export default DownloadPanel;
