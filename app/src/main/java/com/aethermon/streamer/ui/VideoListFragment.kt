package com.aethermon.streamer.ui

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.view.ViewGroup
import androidx.core.view.isVisible
import androidx.fragment.app.Fragment
import androidx.fragment.app.activityViewModels
import androidx.lifecycle.lifecycleScope
import androidx.navigation.fragment.findNavController
import com.aethermon.streamer.databinding.FragmentVideoListBinding
import com.google.android.material.snackbar.Snackbar
import kotlinx.coroutines.launch

class VideoListFragment : Fragment() {

    private var _binding: FragmentVideoListBinding? = null
    private val binding get() = _binding!!
    private val viewModel: VideoViewModel by activityViewModels()
    private val adapter = VideoAdapter { video ->
        val action = VideoListFragmentDirections.actionVideoListToPlayer(video)
        findNavController().navigate(action)
    }

    override fun onCreateView(
        inflater: LayoutInflater, container: ViewGroup?, savedInstanceState: Bundle?
    ): View {
        _binding = FragmentVideoListBinding.inflate(inflater, container, false)
        return binding.root
    }

    override fun onViewCreated(view: View, savedInstanceState: Bundle?) {
        super.onViewCreated(view, savedInstanceState)
        binding.recyclerView.adapter = adapter

        viewModel.authReady.observe(viewLifecycleOwner) { ready ->
            if (ready) signInAndLoad()
        }

        viewModel.videos.observe(viewLifecycleOwner) { state ->
            when (state) {
                is UiState.Loading -> {
                    binding.progressBar.isVisible = true
                    binding.recyclerView.isVisible = false
                    binding.emptyText.isVisible = false
                }
                is UiState.Success -> {
                    binding.progressBar.isVisible = false
                    if (state.data.isEmpty()) {
                        binding.emptyText.isVisible = true
                        binding.recyclerView.isVisible = false
                    } else {
                        binding.recyclerView.isVisible = true
                        binding.emptyText.isVisible = false
                        adapter.submitList(state.data)
                    }
                }
                is UiState.Error -> {
                    binding.progressBar.isVisible = false
                    Snackbar.make(binding.root, state.message, Snackbar.LENGTH_LONG).show()
                }
            }
        }
    }

    private fun signInAndLoad() {
        viewLifecycleOwner.lifecycleScope.launch {
            runCatching {
                val token = viewModel.authManager.getValidToken(requireActivity())
                viewModel.loadVideos(token)
            }.onFailure {
                Snackbar.make(binding.root, it.message ?: "Auth failed", Snackbar.LENGTH_LONG)
                    .show()
            }
        }
    }

    override fun onDestroyView() {
        super.onDestroyView()
        _binding = null
    }
}
